from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from models.baseModel import Base

class request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_status: Mapped[str] = mapped_column(String(45))
    ticket_id: Mapped[int] = mapped_column()
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    install_id: Mapped[int] = mapped_column(ForeignKey("installs.id"), nullable=True)