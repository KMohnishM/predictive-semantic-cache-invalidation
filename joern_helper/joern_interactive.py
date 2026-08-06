from cpgqls_client import CPGQLSClient, CPGQLSTransport, import_code_query
import re
import json
import subprocess
import os
import sys
import uuid
import base64
import websockets


import inspect


class JoernConsoleError(RuntimeError):
    """Raised when Joern returns a console error payload in stdout."""


class JoernResultError(RuntimeError):
    """Raised when a Joern query does not return the expected scalar result."""


class AuthenticatedCPGQLSTransport(CPGQLSTransport):
    """
    CPGQLS Transport wrapper supporting HTTP Basic Authentication headers
    during WebSocket connection handshakes and HTTP requests.
    """
    def __init__(self, auth_credentials=None):
        super().__init__()
        self.auth_credentials = auth_credentials

    def connect(self, endpoint):
        headers = {}
        if self.auth_credentials and isinstance(self.auth_credentials, (tuple, list)) and len(self.auth_credentials) >= 2:
            user_pass = f"{self.auth_credentials[0]}:{self.auth_credentials[1]}"
            b64_creds = base64.b64encode(user_pass.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {b64_creds}"

        sig = inspect.signature(websockets.connect)
        kwargs = {"ping_interval": None}
        if headers:
            if "additional_headers" in sig.parameters:
                kwargs["additional_headers"] = headers
            elif "extra_headers" in sig.parameters:
                kwargs["extra_headers"] = headers

        self._ws_conn = websockets.connect(endpoint, **kwargs)
        return self._ws_conn


class JoernSession:
    """
    Session wrapper for interacting with a Joern server (e.g. localhost:8080 or localhost:8081)
    to query Code Property Graph (CPG) metrics, control flow, and data flow.
    """

    def __init__(self, repo_path: str, endpoint: str = None, auth_credentials: tuple = None):
        self.repo_path = repo_path
        self.project_name = f"joern_{uuid.uuid4().hex[:8]}"

        # Resolve auth credentials from parameter or environment variables
        if auth_credentials is None:
            user = os.getenv("JOERN_AUTH_USERNAME") or os.getenv("JOERN_USERNAME") or os.getenv("JOERN_USER")
            password = os.getenv("JOERN_AUTH_PASSWORD") or os.getenv("JOERN_PASSWORD") or os.getenv("JOERN_PASS")
            if user and password:
                auth_credentials = (user, password)
        self.auth_credentials = auth_credentials

        # Candidate endpoints to try
        endpoints_to_try = []
        if endpoint:
            endpoints_to_try.append(endpoint)
        env_endpoint = os.getenv("JOERN_ENDPOINT") or os.getenv("JOERN_SERVER")
        if env_endpoint and env_endpoint not in endpoints_to_try:
            endpoints_to_try.append(env_endpoint)
        for default_ep in ["localhost:8080", "localhost:8081"]:
            if default_ep not in endpoints_to_try:
                endpoints_to_try.append(default_ep)

        connected = False
        last_error = None

        for ep in endpoints_to_try:
            try:
                transport = AuthenticatedCPGQLSTransport(auth_credentials=self.auth_credentials)
                self.client = CPGQLSClient(ep, transport=transport, auth_credentials=self.auth_credentials)
                self.endpoint = ep
                print(f"[INFO] Connected to Joern server at {ep}")
                self._import_cpg()
                connected = True
                break
            except Exception as e:
                last_error = e
                print(f"[INFO] Failed to initialize Joern session on {ep} ({e}). Trying fallback...")

        if not connected:
            raise ConnectionError(
                f"Failed to connect to Joern server. Last error: {last_error}\n"
                "Ensure Joern is running via 'joern --server' (default port 8080/8081) "
                "and set JOERN_AUTH_USERNAME / JOERN_AUTH_PASSWORD if server requires basic auth."
            ) from last_error

    def _clean_joern_output(self, response: dict):
        """
        Cleans the raw stdout returned by the Joern REPL.
        Handles ANSI escape codes, Scala string wrappers, quotes, and JSON decoding.
        """
        if not response.get("success", False):
            raise RuntimeError(f"Joern query failed:\n{response}")

        stdout = response.get("stdout", "")

        if "io.joern.console.Error" in stdout or "No projects loaded" in stdout:
            raise JoernConsoleError(stdout.strip())

        # Remove ANSI colour sequences
        stdout = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", stdout).strip()

        # Remove everything before '='
        if "=" in stdout:
            value = stdout.split("=", 1)[1].strip()
        else:
            value = stdout

        # Remove Scala string wrappers
        if value.startswith('"""') and value.endswith('"""'):
            value = value[3:-3]
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
            value = bytes(value, "utf-8").decode("unicode_escape")

        value = value.strip()

        # Attempt JSON decoding
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        return value

    def _build_cpg(self):
        """Builds the binary CPG using joern-parse (OS-aware)."""
        parent_dir = os.path.dirname(os.path.abspath(self.repo_path))
        cpg_path = os.path.normpath(os.path.join(parent_dir, "cpg.bin"))

        if os.path.exists(cpg_path):
            print(f"[INFO] CPG already exists at {cpg_path}. Skipping build.")
            return cpg_path

        binary_name = "joern-parse.bat" if sys.platform == "win32" else "joern-parse"
        print(f"[INFO] Building CPG for repository at {self.repo_path} using {binary_name}...")

        subprocess.run(
            [binary_name, str(self.repo_path), "--output", str(cpg_path)],
            check=True,
        )

        print(f"[INFO] CPG built successfully at {cpg_path}.")
        return cpg_path

    def _import_cpg(self):
        """Imports the repository into the active Joern server session."""
        repo_input_path = os.path.abspath(self.repo_path).replace("\\", "/")
        print(f"[INFO] Importing Joern project {self.project_name} from {repo_input_path}...")

        import_query = import_code_query(repo_input_path, self.project_name)
        result = self.client.execute(import_query)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        if not result.get("success") or (stderr and "error" in stderr.lower()) or "Error:" in stdout:
            raise RuntimeError(
                "Failed to import Joern project:\n"
                f"stdout: {stdout}\n"
                f"stderr: {stderr}"
            )

        # Smoke-check that the imported project is actually usable before feature queries run.
        smoke_result = self.execute("cpg.method.size")
        try:
            int(smoke_result)
        except (TypeError, ValueError) as e:
            raise JoernResultError(
                f"Imported CPG did not respond with a numeric method count: {smoke_result!r}"
            ) from e

        print("[INFO] Joern project imported successfully.")

    def _execute_int(self, query: str, description: str) -> int:
        """Execute a Joern query and require an integer scalar response."""
        result = self.execute(query)
        try:
            return int(result)
        except (TypeError, ValueError) as e:
            raise JoernResultError(
                f"{description} returned a non-numeric result: {result!r}"
            ) from e

    def rebuild_cpg(self):
        """Re-imports the current repository snapshot into a fresh Joern project."""
        self.project_name = f"joern_{uuid.uuid4().hex[:8]}"
        self._import_cpg()

    def execute(self, query: str):
        """Executes a CPGQL query and returns cleaned output."""
        return self._clean_joern_output(self.client.execute(query))

    def _literal_regex(self, value: str):
        """Escapes string characters safely for CPGQL regex queries."""
        escaped = re.escape(value).replace("\\", "\\\\")
        return f"^{escaped}$"

    # -------------------------------------------------------------------------
    # File & Symbol Lookup Queries
    # -------------------------------------------------------------------------

    def get_all_files(self):
        query = 'cpg.file.name.l.toJson'
        return self.execute(query)

    def get_all_methods_with_files(self) -> list:
        """
        Returns all methods in the CPG along with short name, full name, and filename.
        Filters out internal compiler wrappers.
        """
        query = 'cpg.method.filterNot(m => m.name.startsWith("<") || m.name.contains("<lambda>")).map(m => (m.name, m.fullName, m.filename)).l.toJson'
        res = self.execute(query)
        return res if isinstance(res, list) else []

    def get_all_call_edges(self) -> list:
        """
        Returns all call graph edges in the CPG as (caller_fullName, list_of_callee_fullNames).
        """
        query = 'cpg.method.filterNot(m => m.name.startsWith("<") || m.name.contains("<lambda>")).map(m => (m.fullName, m.callee.filterNot(c => c.name.startsWith("<") || c.name.contains("<lambda>")).fullName.l)).l.toJson'
        res = self.execute(query)
        return res if isinstance(res, list) else []

    def get_true_names(self, file: str):
        # Match file as a substring of the full path using forward slashes
        clean_file = str(file).replace("\\", "/").strip("./")
        pattern = re.escape(clean_file)
        query = f'cpg.method.filename(".*{pattern}.*").map(m => (m.name, m.fullName)).l.toJson'
        return self.execute(query)

    # -------------------------------------------------------------------------
    # Call Graph Queries
    # -------------------------------------------------------------------------

    def get_direct_callers(self, true_name: str) -> list:
        pattern = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{pattern}").caller.fullName.l.toJson'
        res = self.execute(query)
        return res if isinstance(res, list) else []

    def get_direct_callees(self, true_name: str) -> list:
        pattern = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{pattern}").callee.fullName.l.toJson'
        res = self.execute(query)
        return res if isinstance(res, list) else []

    def get_callers(self, true_name: str) -> list:
        pattern = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{pattern}").repeat(_.caller)(_.emit).fullName.l.toJson'
        res = self.execute(query)
        return res if isinstance(res, list) else []

    def get_callees(self, true_name: str) -> list:
        pattern = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{pattern}").repeat(_.callee)(_.emit).fullName.l.toJson'
        res = self.execute(query)
        return res if isinstance(res, list) else []

    def in_degree(self, true_name: str) -> int:
        return len(self.get_direct_callers(true_name))

    def out_degree(self, true_name: str) -> int:
        return len(self.get_direct_callees(true_name))

    # -------------------------------------------------------------------------
    # Control Flow (CFG) Metrics
    # -------------------------------------------------------------------------

    def cfg_node_count(self, true_name: str) -> int:
        """Counts total control flow instruction nodes in the function."""
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").cfgNode.size'
        return self._execute_int(query, "CFG node count")

    def cyclomatic_complexity(self, true_name: str) -> int:
        """Computes McCabe's Cyclomatic Complexity (M = decision_points + 1)."""
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").controlStructure.size'
        return self._execute_int(query, "Cyclomatic complexity") + 1

    def cfg_nesting_depth(self, true_name: str) -> list:
        """
        Computes nesting depth for each control structure in the function.
        Walks up the AST (inAstMinusLeaf) to count how many ancestors are control structures.
        """
        safe_name = self._literal_regex(true_name)
        query = (
            f'cpg.method.fullName("{safe_name}").controlStructure.map(cs => '
            f'Map("lineNumber" -> cs.lineNumber, '
            f'"depth" -> cs.inAstMinusLeaf.isControlStructure.size)).l.toJson'
        )
        return self.execute(query)

    def max_cfg_nesting_depth(self, true_name: str) -> int:
        """Returns the maximum nesting depth as a single scalar integer."""
        safe_name = self._literal_regex(true_name)
        query = (
            f'cpg.method.fullName("{safe_name}").controlStructure.map(cs => '
            f'cs.inAstMinusLeaf.isControlStructure.size).l.maxOption.getOrElse(0)'
        )
        return self._execute_int(query, "Max CFG nesting depth")

    # -------------------------------------------------------------------------
    # Data Flow (PDG) & Taint Reachability Queries
    # -------------------------------------------------------------------------

    def data_flow_distance(self, true_name: str, modified_name: str = None) -> int:
        """
        Returns the minimum data-flow distance from a modified_name method (or internal parameter)
        to CFG nodes inside true_name.
        Returns 0 if no data-flow paths exist.
        """
        safe_name = self._literal_regex(true_name)
        source_target = (
            f'cpg.method.fullName("{self._literal_regex(modified_name)}").ast'
            if modified_name else
            f'cpg.method.fullName("{safe_name}").parameter'
        )

        query = f'''
    cpg.method
    .fullName("{safe_name}")
    .cfgNode
    .reachableByFlows({source_target})
    .map(flow => flow.elements.size - 1)
    .l
    .toJson
    '''
        distances = self.execute(query)
        if not distances or not isinstance(distances, list):
            return 0
        return min(distances)

    def modified_data_deps_count(self, true_name: str, modified_name: str = None) -> int:
        """Returns the total number of data-flow paths reaching true_name from modified_name."""
        safe_name = self._literal_regex(true_name)
        source_target = (
            f'cpg.method.fullName("{self._literal_regex(modified_name)}")'
            if modified_name else
            f'cpg.method.fullName("{safe_name}").parameter'
        )

        query = f'''
    cpg.method
    .fullName("{safe_name}")
    .cfgNode
    .reachableByFlows({source_target})
    .size
    '''
        return self._execute_int(query, "Modified data dependencies count")

    def taint_reachability_score(self, true_name: str, modified_name: str = None) -> float:
        """Returns 1.0 if modified data flows into true_name, else 0.0."""
        dist = self.data_flow_distance(true_name, modified_name)
        return 1.0 if dist > 0 else 0.0

    # -------------------------------------------------------------------------
    # Method Signatures & Graph Distance Helpers
    # -------------------------------------------------------------------------

    def method_signature(self, true_name: str) -> str:
        """Returns the method signature string to check for parameter/return mutations."""
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").signature'
        return str(self.execute(query))

    def distance_to_modified(self, true_name: str, modified_names: list, directed: bool = True) -> int:
        """
        Calculates the minimum hop distance in the call graph from true_name to any node in modified_names.
        Returns -1 if unreachable.
        """
        for mod_name in modified_names:
            if mod_name == true_name:
                return 0

        # Check immediate direct (1-hop) neighbors
        direct_callers = self.get_direct_callers(true_name)
        direct_callees = self.get_direct_callees(true_name) if not directed else []
        direct_neighbors = set(direct_callers + direct_callees)

        for mod_name in modified_names:
            if mod_name in direct_neighbors:
                return 1

        # Check multi-hop
        min_dist = 999
        for mod_name in modified_names:
            pattern = self._literal_regex(true_name)
            target_pattern = self._literal_regex(mod_name)
            query = f'cpg.method.fullName("{pattern}").repeat(_.caller)(_.until(_.fullName("{target_pattern}"))).path.l.size'
            res = self.execute(query)
            if res and int(res) > 0:
                min_dist = min(min_dist, int(res))

        return min_dist if min_dist != 999 else -1

    def modified_dependents_count(self, true_name: str, modified_names: list) -> int:
        """Counts how many modified nodes depend on (call) true_name."""
        callers = set(self.get_callers(true_name))
        return len(callers.intersection(set(modified_names)))


if __name__ == "__main__":
    session = JoernSession("workspace/black")

    files_in_repo = session.get_all_files()
    print(f"Files in repository: {len(files_in_repo)} files found")
    print("==================================================")
    print("JOERN CPG FEATURE EXTRACTION DEMO")
    print("==================================================")

    sample_method = "run_experiment.py:<module>.Experiment.setup"
    sample_mod = ["run_experiment.py:<module>.main"]

    print(f"Target Method: {sample_method}\n")
    print(f"1.  In-degree:                       {session.in_degree(sample_method)}")
    print(f"2.  Out-degree:                      {session.out_degree(sample_method)}")
    print(f"3.  Transitive Callers Count:        {len(session.get_callers(sample_method))}")
    print(f"4.  Transitive Callees Count:        {len(session.get_callees(sample_method))}")
    print(f"5.  CFG Node Count:                  {session.cfg_node_count(sample_method)}")
    print(f"6.  Cyclomatic Complexity (McCabe M):{session.cyclomatic_complexity(sample_method)}")
    print(f"7.  Max CFG Nesting Depth:          {session.max_cfg_nesting_depth(sample_method)}")
    print(f"8.  Data-Flow Distance:              {session.data_flow_distance(sample_method)}")
    print(f"9.  Modified Data Deps Count:        {session.modified_data_deps_count(sample_method)}")
    print(f"10. Taint Reachability Score:        {session.taint_reachability_score(sample_method)}")
    print(f"11. Distance to Modified (Directed):  {session.distance_to_modified(sample_method, sample_mod, directed=True)}")
    print(f"12. Distance to Modified (Undirected):{session.distance_to_modified(sample_method, sample_mod, directed=False)}")
    print(f"13. Modified Dependents Count:       {session.modified_dependents_count(sample_method, sample_mod)}")
    print(f"14. Method Signature:                {session.method_signature(sample_method)}")
    print("==================================================")