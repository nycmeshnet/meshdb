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
from meshdb.models.baseModel import Base


class RequestStatusEnum(Enum):
    Open = "Open"
    Closed = "Closed"
    Installed = "Installed"


class request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_status: Mapped[RequestStatusEnum] = mapped_column(
        SQLAlchemyEnum(RequestStatusEnum), nullable=False
    )
    ticket_id: Mapped[int] = mapped_column()
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    install_id: Mapped[int] = mapped_column(ForeignKey("installs.id"), nullable=True)
