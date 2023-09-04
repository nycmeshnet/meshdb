from unittest import mock

from meshdb.data.database import load_db_string_from_env


def test_db_string_generator():
    with mock.patch.dict(
        "os.environ",
        {
            "DB_USER": "admin",
            "DB_PASSWORD": "password123",
            "DB_HOST": "localhost",
            "DB_NAME": "mesh-db",
        },
    ):
        db_string = load_db_string_from_env()
        assert db_string == "postgresql://admin:password123@localhost/mesh-db"
