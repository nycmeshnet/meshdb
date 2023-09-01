from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from meshdb.auth.token import authToken, userRole
from meshdb.db.database import create_db_engine, executeQuery

db_engine = create_db_engine()


def getUserRole(token: str) -> str:
    stmt = select(authToken.role).where(authToken.token == token)
    result = executeQuery(stmt, db_engine)
    return result.one()[0]


def addAPIUser(token: str, email: str, slackhandle: str, role: str) -> None:
    newUser = authToken(token=token, email=email, slackhandle=slackhandle, role=role)
    with Session(db_engine) as session:
        session.add_all([newUser])
        session.commit()


def getRolePermission(token: str, role: str) -> bool:
    returnedRole = getUserRole(token)
    stmt = select(getattr(userRole, role)).where(userRole.rolename == returnedRole)
    result = executeQuery(stmt, db_engine)
    return result.one()[0]
