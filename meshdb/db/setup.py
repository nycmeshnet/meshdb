from sqlalchemy_utils import create_database, database_exists

import meshdb.models.baseModel
import meshdb.models.building
import meshdb.models.install
import meshdb.models.member
import meshdb.models.request

from ..db.database import create_db_engine


def setup_db():
    engine = create_db_engine() # TODO: Delete?

    if not database_exists(engine.url):
        print("Database not found. Bootstrapping....")
        create_database(engine.url)
    print(database_exists(engine.url))
    meshdb.models.baseModel.Base.metadata.create_all(engine)
