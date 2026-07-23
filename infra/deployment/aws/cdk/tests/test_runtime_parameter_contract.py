import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "flowform_infra/config/runtime_parameter_contract.py"
SPEC = importlib.util.spec_from_file_location("runtime_parameter_contract", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
scope_parameter_name = MODULE.scope_parameter_name


def test_scope_parameter_names_are_shared_with_rehearsal_contract():
    assert scope_parameter_name("nonprod", "kms_key_arn") == "/flowform/nonprod/kms-key-arn"
    assert scope_parameter_name("prod", "linkage_secret_arn") == "/flowform/prod/linkage-secret-arn"
