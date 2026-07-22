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

    def get_all_files(self):
        query = 'cpg.file.name.l.toJson'
        return self.execute(query)

    def get_true_names(self, file: str):
        query = f'cpg.method.filename(".*{file}").map(m => (m.name, m.fullName)).l.toJson'
        return self.execute(query)

    def get_callers(self, true_name: str):
        query = f'cpg.method.fullName("{true_name}").repeat(_.caller)(_.emit).fullName.l.toJson'
        return self.execute(query)

    def get_callees(self, true_name: str):
        query = f'cpg.method.fullName("{true_name}").repeat(_.callee)(_.emit).fullName.l.toJson'
        return self.execute(query)

if __name__ == "__main__":

    session = JoernSession("C:\\Users\\admin\\Desktop\\Career\\Project-1\\Embeddings Generator\\repos")

    files_in_repo = session.get_all_files()
    print(f"Files in repository: {files_in_repo}")
    
    true_names = session.get_true_names("run_experiment.py")
    print(f"True names in 'run_experiment.py': {true_names}")

    print("Callers of 'run_experiment':")
    callers = session.get_callers("run_experiment.py:<module>.Experiment.setup")
    print(callers)

    print("Callees of 'run_experiment':")
    callees = session.get_callees("run_experiment.py:<module>.Experiment.setup")
    print(callees)