from enum import Enum
from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date, TEXT
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from meshdb.models.baseModel import Base


# TODO: Elaborate on this
class BuildingStatusEnum(Enum):
    Active = "Active"
    Inactive = "Inactive"


class building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    bin: Mapped[int] = mapped_column()
    building_status: Mapped[BuildingStatusEnum] = mapped_column(
        SQLAlchemyEnum(BuildingStatusEnum), nullable=False
    )
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
