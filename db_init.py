import variables
from sqlalchemy_utils import database_exists, create_database


##MODELS NEED TO BE IMPORTED HERE
import models.baseModel
import models.building
import models.member
import models.request
import models.baseModel
import models.install



from sqlalchemy import create_engine

def main():

    engine = create_engine("postgresql://{}:{}@{}/{}".format(variables.db_user,
                                                             variables.db_password,
                                                             variables.db_host,
                                                             variables.db_name), echo=True)
    if not database_exists(engine.url):
        create_database(engine.url)
    print(database_exists(engine.url))
    models.baseModel.Base.metadata.create_all(engine)

if __name__ == "__main__":
    main()