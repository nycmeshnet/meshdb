from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from baseModel import Base

class member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    emailAddress: Mapped[str] = mapped_column(String(45))
    phoneNumber: Mapped[str] = mapped_column(String(20), nullable=True)
    slackHandle: Mapped[str] = mapped_column(String(45), nullable=True)