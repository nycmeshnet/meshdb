from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date, TEXT
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from models.baseModel import Base


class building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(45))
    streetAddress: Mapped[str] = mapped_column(TEXT)
    city: Mapped[str] = mapped_column(String(45))
    state: Mapped[str] = mapped_column(String(45))
    zipCode: Mapped[int] = mapped_column()
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    altitude: Mapped[float] = mapped_column()


    networkNumber: Mapped[int] = mapped_column(nullable=True)
    installDate: Mapped[datetime.date] = mapped_column(nullable=True)
    abandonDate: Mapped[datetime.date] = mapped_column(nullable=True)
    panoramaImage: Mapped[str] = mapped_column(TEXT, nullable=True)