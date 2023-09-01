from unittest import mock

from meshdb.db.database import load_db_string_from_env


def test_db_string_generator():
    with mock.patch.dict(
        "os.environ",
        {
            "MESHDB_DB_USER": "admin",
            "MESHDB_DB_PASSWORD": "password123",
            "MESHDB_DB_HOST": "localhost",
            "MESHDB_DB_NAME": "mesh-db",
        },
    ):
        db_string = load_db_string_from_env()
        assert db_string == "postgresql://admin:password123@localhost/mesh-db"
