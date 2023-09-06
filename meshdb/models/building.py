import datetime
from enum import Enum

from sqlalchemy import TEXT
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from ..data.database import db


# TODO: Elaborate on this
class BuildingStatusEnum(Enum):
    Active = "Active"
    Inactive = "Inactive"


class building(db.Model):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    bin: Mapped[int] = mapped_column()
    building_status: Mapped[BuildingStatusEnum] = mapped_column(SQLAlchemyEnum(BuildingStatusEnum), nullable=False)
    street_address: Mapped[str] = mapped_column(TEXT)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    zip_code: Mapped[int] = mapped_column()
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    altitude: Mapped[float] = mapped_column()

    network_number: Mapped[int] = mapped_column(nullable=True)
    install_date: Mapped[datetime.date] = mapped_column(nullable=True)
    abandon_date: Mapped[datetime.date] = mapped_column(nullable=True)
    panorama_image: Mapped[str] = mapped_column(TEXT, nullable=True)
