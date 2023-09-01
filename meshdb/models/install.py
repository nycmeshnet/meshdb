from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..models.baseModel import Base


class InstallStatusEnum(Enum):
    Active = "Active"
    Inactive = "Inactive"
    Planned = "Planned"


class install(Base):
    __tablename__ = "installs"

    id: Mapped[int] = mapped_column(primary_key=True)
    install_number: Mapped[int] = mapped_column()
    install_status: Mapped[InstallStatusEnum] = mapped_column(SQLAlchemyEnum(InstallStatusEnum), nullable=False)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
