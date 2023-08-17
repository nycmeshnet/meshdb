from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from baseModel import Base

class request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(45))
    TicketId: Mapped[int] = mapped_column()
    memberId: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=True)
    buildingId: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    installId: Mapped[int] = mapped_column(ForeignKey("installs.id"), nullable=True)