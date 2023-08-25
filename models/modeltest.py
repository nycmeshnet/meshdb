from sqlalchemy import create_engine

engine = create_engine("sqlite://", echo=True)
