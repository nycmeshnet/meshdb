from enum import Enum
from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date, ForeignKey
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from models.baseModel import Base


class InstallStatusEnum(Enum):
    Active = "Active"
    Inactive = "Inactive"
    Planned = "Planned"


class install(Base):
    __tablename__ = "installs"

    id: Mapped[int] = mapped_column(primary_key=True)
    install_number: Mapped[int] = mapped_column()
    install_status: Mapped[InstallStatusEnum] = mapped_column(
        SQLAlchemyEnum(InstallStatusEnum), nullable=False
    )
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
