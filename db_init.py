from sqlalchemy_utils import database_exists, create_database
from db.database import create_db_engine


##MODELS NEED TO BE IMPORTED HERE
import models.baseModel
import models.building
import models.member
import models.request
import models.baseModel
import models.install
import auth.token


from sqlalchemy import create_engine


def db_init():
    engine = create_db_engine()

    if not database_exists(engine.url):
        create_database(engine.url)
    print(database_exists(engine.url))
    models.baseModel.Base.metadata.create_all(engine)
