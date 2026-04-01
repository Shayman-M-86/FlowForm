from helpers import current_database_name


def test_backend_can_connect_to_both_databases() -> None:
    assert current_database_name("DATABASE_CORE") == "flowform_core"
    assert current_database_name("DATABASE_RESPONSE") == "flowform_response"
