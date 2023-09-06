from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from ..data.database import db



class member(db.Model):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email_address: Mapped[str] = mapped_column(String)
    phone_number: Mapped[str] = mapped_column(String, nullable=True)
    slack_handle: Mapped[str] = mapped_column(String, nullable=True)
