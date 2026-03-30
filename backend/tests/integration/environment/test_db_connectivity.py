from helpers import current_database_name


def test_backend_can_connect_to_both_databases() -> None:
    assert current_database_name("FF_PGDB_CORE") == "flowform_core"
    assert current_database_name("FF_PGDB_RESPONSE") == "flowform_response"
