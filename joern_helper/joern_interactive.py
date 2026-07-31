from cpgqls_client import CPGQLSClient
import re
import json
import subprocess
import os
import sys


class JoernSession:
    """
    Session wrapper for interacting with a Joern server (localhost:8080)
    to query Code Property Graph (CPG) metrics, control flow, and data flow.
    """

    def __init__(self, repo_path: str, endpoint: str = "localhost:8080"):
        self.repo_path = repo_path
        self.endpoint = endpoint
        
        try:
            self.client = CPGQLSClient(endpoint)
            print(f"[INFO] Connected to Joern server at {endpoint}")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Joern server at {endpoint}. "
                "Ensure Joern is running via 'joern --server'."
            ) from e

        self.cpg_path = self._build_cpg()
        self._import_cpg()

    def _clean_joern_output(self, response: dict):
        """
        Cleans the raw stdout returned by the Joern REPL.
        Handles ANSI escape codes, Scala string wrappers, quotes, and JSON decoding.
        """
        if not response.get("success", False):
            raise RuntimeError(f"Joern query failed:\n{response}")

        stdout = response.get("stdout", "")

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
        """Imports the generated CPG into the active Joern server session."""
        escaped = str(self.cpg_path).replace("\\", "\\\\")
        print("[INFO] Importing CPG...")

        result = self.client.execute(f'importCpg("{escaped}")')
        if not result.get("success"):
            raise RuntimeError("Failed to import CPG.")

        print("[INFO] CPG imported successfully.")

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

    def get_true_names(self, file: str):
        # Match file as a substring of the full path that Joern stores in `filename`
        pattern = re.escape(file).replace("\\", "\\\\")
        query = f'cpg.method.filename(".*{pattern}").map(m => (m.name, m.fullName)).l.toJson'
        return self.execute(query)

    # -------------------------------------------------------------------------
    # Call Graph Queries
    # -------------------------------------------------------------------------

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
        pattern = self._literal_regex(true_name)
        res = self.execute(f'cpg.method.fullName("{pattern}").caller.fullName.l.toJson')
        return len(res) if isinstance(res, list) else 0

    def out_degree(self, true_name: str) -> int:
        pattern = self._literal_regex(true_name)
        res = self.execute(f'cpg.method.fullName("{pattern}").callee.fullName.l.toJson')
        return len(res) if isinstance(res, list) else 0

    # -------------------------------------------------------------------------
    # Control Flow (CFG) Metrics
    # -------------------------------------------------------------------------

    def cfg_node_count(self, true_name: str) -> int:
        """Counts total control flow instruction nodes in the function."""
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").cfgNode.size'
        return int(self.execute(query))

    def cyclomatic_complexity(self, true_name: str) -> int:
        """Computes McCabe's Cyclomatic Complexity (M = decision_points + 1)."""
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").controlStructure.size'
        return int(self.execute(query)) + 1

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
        return int(self.execute(query))

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
        result = self.execute(query)
        return int(result)

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
        callers = self.get_callers(true_name)
        callees = self.get_callees(true_name) if not directed else []
        neighbors = set(callers + callees)

        for mod_name in modified_names:
            if mod_name == true_name:
                return 0
            if mod_name in neighbors:
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