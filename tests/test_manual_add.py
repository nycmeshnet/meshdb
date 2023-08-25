from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select
from models.member import member
from models.building import building
from models.install import install
from db.database import create_db_engine


def test_data():
    engine = create_db_engine()
    with Session(engine) as session:
        daniel = member(
            first_name="Daniel",
            last_name="Heredia",
            email_address="dheredia@nycmesh.net",
        )
        danielBuilding = building(
            building_status="Active",
            street_address="1615 Summerfield St",
            city="Queens",
            state="NY",
            zip_code=11385,
            latitude=40.695140,
            longitude=-73.902410,
            altitude=1,
        )
        danielInstall = install(
            install_number=69420,
            install_status="Active",
            building_id="1",
            member_id="1",
        )
        session.add(danielBuilding)
        session.commit()

        session.add(daniel)
        session.commit()

        session.add(danielInstall)
        session.commit()
