import json
import os
from pathlib import Path
import subprocess
import sys


APP=Path(__file__).resolve().parents[2]/"apps"/"client-contracts"


def run_cli(*args):
    return subprocess.run([sys.executable,"-m","client_contracts.cli",*args],capture_output=True,text=True,encoding="utf-8",env={**os.environ,"PYTHONPATH":str(APP)})


def test_cli_exports_validates_and_checks_client(tmp_path):
    output=tmp_path/"bundle.json"; command=tmp_path/"command.json"
    command.write_text(json.dumps({"contractId":"CMD-RUN-START","contractVersion":"1.0","operationId":"start-1","correlationId":"corr-1","payload":{}}),encoding="utf-8")

    exported=run_cli("export","--output",str(output),"--json")
    validated=run_cli("validate-command","--input",str(command),"--expected-contract","CMD-RUN-START","--json")
    compatible=run_cli("check-client","--client-version","1.2.0","--json")

    assert exported.returncode==validated.returncode==compatible.returncode==0
    assert json.loads(validated.stdout)["resultClass"]=="VALID"
    assert json.loads(compatible.stdout)["resultClass"]=="COMPATIBLE"
