from typing import List
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, Date
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
from models.baseModel import Base


class member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(45))
    last_name: Mapped[str] = mapped_column(String(45))
    email_address: Mapped[str] = mapped_column(String(45))
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    slack_handle: Mapped[str] = mapped_column(String(45), nullable=True)
