from cpgqls_client import CPGQLSClient

import re
import json
import subprocess
import os


class JoernSession:

    def __init__(self, repo_path: str, endpoint: str = "localhost:8080"):
        self.repo_path = repo_path
        self.endpoint = endpoint
        self.client = CPGQLSClient(endpoint)

        print(f"[INFO] Connected to Joern server at {endpoint}")

        self.cpg_path = self._build_cpg()

        self._import_cpg()

    def _clean_joern_output(self, response: dict):
        """
        Cleans the output returned by the Joern REPL.

        Handles:
        - ANSI escape codes
        - Regular quoted Scala strings
        - Triple-quoted Scala strings
        - Non-JSON outputs (returns as plain text)
        """

        if not response.get("success", False):
            raise RuntimeError(
                f"Joern query failed:\n{response}"
            )

        stdout = response.get("stdout", "")

        # Remove ANSI colour sequences
        stdout = re.sub(
            r"\x1B\[[0-?]*[ -/]*[@-~]",
            "",
            stdout,
        ).strip()

        # Remove everything before '='
        if "=" in stdout:
            value = stdout.split("=", 1)[1].strip()
        else:
            value = stdout

        # -----------------------------
        # Remove Scala string wrappers
        # -----------------------------

        # Triple quoted string
        if value.startswith('"""') and value.endswith('"""'):
            value = value[3:-3]

        # Normal quoted string
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

            # Convert escaped characters
            value = bytes(value, "utf-8").decode("unicode_escape")

        value = value.strip()

        # -----------------------------
        # Try JSON
        # -----------------------------
        try:
            return json.loads(value)

        except json.JSONDecodeError:
            pass

        # -----------------------------
        # Not JSON
        # -----------------------------
        return value

    def _build_cpg(self):

        cpg_path =  f"{self.repo_path}/../cpg.bin"

        if os.path.exists(cpg_path):
            print(f"[INFO] CPG already exists at {cpg_path}. Skipping build.")
            return cpg_path

        print(f"[INFO] Building CPG for repository at {self.repo_path}...")
        subprocess.run(
            [
                "joern-parse.bat",
                str(self.repo_path),
                "--output",
                str(cpg_path),
            ],
            check=True,
        )

        print(f"[INFO] CPG built successfully at {cpg_path}.")

        return cpg_path

    def _import_cpg(self):
        escaped = str(self.cpg_path).replace("\\", "\\\\")

        print("[INFO] Importing CPG...")

        result = self.client.execute(
            f'importCpg("{escaped}")'
        )

        if not result.get("success"):
            raise RuntimeError("Failed to import CPG.")

        print("[INFO] CPG imported.")

    def execute(self, query: str):
        return self._clean_joern_output(self.client.execute(query))

    def _literal_regex(self, value: str):
        escaped = re.escape(value).replace("\\", "\\\\")
        return f"^{escaped}$"

    def get_all_files(self):
        query = 'cpg.file.name.l.toJson'
        return self.execute(query)

    def get_true_names(self, file: str):
        pattern = self._literal_regex(file)
        query = f'cpg.method.filename(".*{pattern}").map(m => (m.name, m.fullName)).l.toJson'
        return self.execute(query)

    def get_callers(self, true_name: str):
        pattern = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{pattern}").repeat(_.caller)(_.emit).fullName.l.toJson'
        return self.execute(query)

    def get_callees(self, true_name: str):
        pattern = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{pattern}").repeat(_.callee)(_.emit).fullName.l.toJson'
        return self.execute(query)

    def in_degree(self, true_name: str):
        return len(self.get_callers(true_name))

    def out_degree(self, true_name: str):
        return len(self.get_callees(true_name))

    def cfg_node_count(self, true_name: str) -> int:
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").cfgNode.size'
        return self.execute(query)

    def cyclomatic_complexity(self, true_name: str) -> int:
        safe_name = self._literal_regex(true_name)
        query = f'cpg.method.fullName("{safe_name}").controlStructure.size'
        return self.execute(query)

    def data_flow_distance(self, true_name: str) -> int:
        """
        Returns the minimum data-flow distance from any parameter to any CFG node
        inside the method.

        Distance = number of edges in the shortest reachable data-flow path.
        Returns 0 if no data-flow paths exist.
        """
        safe_name = self._literal_regex(true_name)

        query = f'''
    cpg.method
    .fullName("{safe_name}")
    .cfgNode
    .reachableByFlows(
        cpg.method.fullName("{safe_name}").parameter
    )
    .map(flow => flow.elements.size - 1)
    .l
    .toJson
    '''

        distances = self.execute(query)

        if not distances:
            return 0

        return min(distances)

    def modified_data_deps_count(self, true_name: str) -> int:
        """
        Returns the total number of data-flow paths originating from
        method parameters.
        """
        safe_name = self._literal_regex(true_name)

        query = f'''
    cpg.method
    .fullName("{safe_name}")
    .cfgNode
    .reachableByFlows(
        cpg.method.fullName("{safe_name}").parameter
    )
    .size
    '''

        result = self.execute(query)

        return int(result)


if __name__ == "__main__":

    session = JoernSession("C:\\Users\\admin\\Desktop\\Career\\Project-1\\predictive-semantic-cache-invalidation\\joern_helper\\repos")

    files_in_repo = session.get_all_files()
    print(f"Files in repository: {files_in_repo}")
    print("--------------------------------------------------")
    
    true_names = session.get_true_names("run_experiment.py")
    print(f"True names in 'run_experiment.py': {true_names}")
    print("--------------------------------------------------")

    print("Callers of 'run_experiment':")
    callers = session.get_callers("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(callers)
    print("--------------------------------------------------")

    print("Callees of 'run_experiment':")
    callees = session.get_callees("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(callees)
    print("--------------------------------------------------")

    print("In-degree of 'run_experiment':")
    in_degree = session.in_degree("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(in_degree)
    print("--------------------------------------------------")

    print("Out-degree of 'run_experiment':")
    out_degree = session.out_degree("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(out_degree)
    print("--------------------------------------------------")

    print("CFG node count of 'run_experiment':")
    cfg_node_count = session.cfg_node_count("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(cfg_node_count)
    print("--------------------------------------------------")

    print("Cyclomatic complexity of 'run_experiment':")
    cyclomatic_complexity = session.cyclomatic_complexity("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(cyclomatic_complexity)
    print("--------------------------------------------------")

    print("Data flow distance of 'run_experiment':")
    data_flow_distance = session.data_flow_distance("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(data_flow_distance)
    print("--------------------------------------------------")

    print("Modified data dependencies count of 'run_experiment':")
    modified_data_deps_count = session.modified_data_deps_count("predictive-semantic-cache-invalidation\\run_experiment.py:<module>.Experiment.setup")
    print(modified_data_deps_count)
    print("--------------------------------------------------")