from models.building import building
from models.install import install
from models.member import member
from models.request import request
from sqlalchemy import select
import variables
from db.database import create_db_engine, executeQuery


# execute query

db_engine = create_db_engine()


# returns list of dicts for each member


def getMembers():
    stmt = select(
        member.id,
        member.firstname,
        member.lastname,
        member.emailaddress,
        member.slackhandle,
    )
    result = executeQuery(stmt, db_engine)
    baselist = []
    for row in result.all():
        baselist.append(dict(zip(result.keys(), row)))
    return baselist


# returns one member dict for a given member ID


def getMemberByID(memberId):
    stmt = select(
        member.id, member.firstname, member.lastname, member.emailaddress
    ).where(member.id == memberId)
    result = executeQuery(stmt, db_engine)
    try:
        response = dict(zip(result.keys(), result.one()))
    except:
        raise ValueError("Member does not exist")
    return response
