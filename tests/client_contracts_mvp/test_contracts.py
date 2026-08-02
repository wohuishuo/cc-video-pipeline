import json
from pathlib import Path
import sys


APP=Path(__file__).resolve().parents[2]/"apps"/"client-contracts"
sys.path.insert(0,str(APP))

from client_contracts.contracts import ClientContracts, ContractError


def test_bundle_names_commands_endpoints_scopes_and_state_owners():
    bundle=ClientContracts().bundle()

    assert bundle["contractVersion"]=="1.0"
    assert set(bundle["commands"])=={"CMD-RUN-CREATE","CMD-RUN-START","CMD-RUN-CANCEL"}
    assert bundle["endpoints"]["POST /api/v1/runs"]["scope"]=="runs:write"
    assert bundle["endpoints"]["GET /api/v1/runs"]["scope"]=="runs:read"
    assert bundle["ownership"]["runState"]=="Video Graph Studio"
    assert bundle["ownership"]["clientProjection"]=="disposable"


def test_export_is_atomic_and_exact_replay_is_duplicate(tmp_path):
    owner=ClientContracts(); path=tmp_path/"client-contracts.json"
    first=owner.export(path); replay=owner.export(path)

    assert first.result_class=="COMPLETED"
    assert replay.result_class=="DUPLICATE_COMPLETED"
    assert first.value["sha256"]==replay.value["sha256"]
    assert list(tmp_path.glob(".client-contracts.json.*.tmp"))==[]


def test_validate_accepts_known_command_and_rejects_wrong_version():
    owner=ClientContracts()
    command={
        "contractId":"CMD-RUN-CREATE","contractVersion":"1.0",
        "operationId":"mobile-op-1","correlationId":"mobile-corr-1","payload":{},
    }
    assert owner.validate_command(command,"CMD-RUN-CREATE").result_class=="VALID"
    command["contractVersion"]="2.0"
    try: owner.validate_command(command,"CMD-RUN-CREATE")
    except ContractError as error: assert error.code=="REJECTED_VERSION"
    else: raise AssertionError("unsupported command version accepted")


def test_validate_rejects_unknown_fields_and_unbounded_identity():
    owner=ClientContracts(); command={
        "contractId":"CMD-RUN-START","contractVersion":"1.0",
        "operationId":"x"*129,"correlationId":"corr","payload":{},"admin":True,
    }
    try: owner.validate_command(command,"CMD-RUN-START")
    except ContractError as error: assert error.code=="REJECTED_MALFORMED"
    else: raise AssertionError("unsafe command accepted")


def test_compatibility_is_bounded_to_declared_major_and_minimum():
    owner=ClientContracts()
    assert owner.check_client("1.0.0").result_class=="COMPATIBLE"
    assert owner.check_client("1.9.2").result_class=="COMPATIBLE"
    assert owner.check_client("0.9.9").result_class=="REJECTED_CLIENT"
    assert owner.check_client("2.0.0").result_class=="REJECTED_CLIENT"
