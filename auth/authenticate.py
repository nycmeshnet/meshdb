from sqlalchemy import create_engine
import variables
from db.database import create_db_engine, executeQuery
from auth.token import authToken
from auth.token import userRole
from sqlalchemy import select
from sqlalchemy.orm import Session

db_engine = create_db_engine()

def getUserRole(token):
    stmt = (
        select(authToken.role).where(authToken.token == token)
    )
    result = executeQuery(stmt, db_engine)
    return result.one()[0]

def addAPIUser(token, email, slackhandle, role):
    newUser = authToken(
        token = token,
        email = email,
        slackhandle = slackhandle,
        role = role
    )
    with Session(db_engine) as session:
        session.add_all([newUser])
        session.commit()

def getRolePermission(token, role):
    returnedRole = getUserRole(token)
    stmt = (
        select(getattr(userRole, role)).where(userRole.rolename == returnedRole)
    )
    result = executeQuery(stmt, db_engine)
    return result.one()[0]