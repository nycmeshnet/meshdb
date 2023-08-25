from sqlalchemy import Column, Integer, DateTime, String, Date, TEXT, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from models.baseModel import Base



class userRole(Base):
    __tablename__ = 'userroles'

    id: Mapped[int] = mapped_column(primary_key=True)
    rolename: Mapped[str] = mapped_column(String(45))
    get: Mapped[bool] = mapped_column()
    put: Mapped[bool] = mapped_column()
    update: Mapped[bool] = mapped_column()
    seemembers: Mapped[bool] = mapped_column()

class authToken(Base):
    __tablename__ = 'authtokens'

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column((String(64)))
    email: Mapped[str] = mapped_column(String(45))
    slackhandle: Mapped[str] = mapped_column((String(45)))
    role: Mapped[str] = mapped_column((String(45)))




