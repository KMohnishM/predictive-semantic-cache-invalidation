# Joern Helper — Quick Start

This guide shows how to download, run and use Joern locally with the Python `cpgqls_client` helper.

## Prerequisites

- Java (required by Joern)
- PowerShell or a POSIX shell (Linux/macOS)
- Python 3.8+ and `pip`

## 1 — Download Joern

1. Visit the Joern releases: https://github.com/joernio/joern/releases
2. Download the appropriate `*_cli.zip` for your platform.
3. Extract the archive to a folder you control (example: `C:\tools\joern` on Windows).
4. (Optional) Add the Joern folder to your PATH so you can run `joern` / `joern.bat` from any shell.

## 2 — Start the Joern server

Open PowerShell (Windows) or a terminal (Linux/macOS) and run the server mode. Example (Windows):

```powershell
joern.bat --server --server-host localhost --server-port 8080
```

On Linux/macOS the equivalent is:

```bash
./joern --server --server-host localhost --server-port 8080
```

Leave this process running while you query the CPG from other tools.

## 3 — Install the Python client

In your Python environment install the `cpgqls_client` package:

```bash
pip install cpgqls_client
```

## 4 — Run the helper script

This repository contains a helper script `joern_interactive.py` that uses the running Joern server. Start it like this (from the `joern_helper` folder):

```bash
python joern_interactive.py
```

If you prefer a minimal example of using the Python client, run your own small script (adjust host/port if needed):

```python
from cpgqls_client import client

# Connect to the Joern HTTP server
c = client.connect('http://localhost:8080')

# Run a simple query (example: list method names)
res = c.run_query('cpg.method.name.l')
print(res)
```

Note: the exact client API may vary by `cpgqls_client` release; check the package docs if `client.connect` or `run_query` are different.

## Troubleshooting

- If `joern` or `joern.bat` is not found, ensure the extracted folder is on your PATH or call it by full path.
- If the server fails to start because the port is in use, pick a different `--server-port` (for example `9090`) and update the client URL accordingly.
- If Python client calls time out, confirm the Joern server process is running and reachable at the host/port you specified.

## References

- Joern releases: https://github.com/joernio/joern/releases
- `cpgqls_client` (PyPI): https://pypi.org/project/cpgqls-client/

---