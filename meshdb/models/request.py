from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..models.baseModel import Base


class RequestStatusEnum(Enum):
    Open = "Open"
    Closed = "Closed"
    Installed = "Installed"


class request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_status: Mapped[RequestStatusEnum] = mapped_column(SQLAlchemyEnum(RequestStatusEnum), nullable=False)
    ticket_id: Mapped[int] = mapped_column()
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    install_id: Mapped[int] = mapped_column(ForeignKey("installs.id"), nullable=True)
