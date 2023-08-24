from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from models.baseModel import Base

class install(Base):
    __tablename__ = "installs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(45))
    buildingid: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    memberid: Mapped[int] = mapped_column(ForeignKey("members.id"))