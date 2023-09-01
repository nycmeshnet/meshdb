from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists

import meshdb.auth.token

##MODELS NEED TO BE IMPORTED HERE
import meshdb.models.baseModel
import meshdb.models.building
import meshdb.models.install
import meshdb.models.member
import meshdb.models.request
from meshdb.db.database import create_db_engine


def setup_db() -> None:
    engine = create_db_engine()

    if not database_exists(engine.url):
        create_database(engine.url)
    print(database_exists(engine.url))
    meshdb.models.baseModel.Base.metadata.create_all(engine)
