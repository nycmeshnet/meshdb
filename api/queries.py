from models.building import building
from models.install import install
from models.member import member
from models.request import request
from sqlalchemy import select
from sqlalchemy.orm import Session
import variables
from sqlalchemy import create_engine


#execute query

db_engine = create_engine("postgresql://{}:{}@{}/{}".format(variables.db_user,
                                                             variables.db_password,
                                                             variables.db_host,
                                                             variables.db_name), echo=True)

def executeQuery(statement, engine):
    with Session(engine) as session:
        return session.execute(statement)
    

# returns list of dicts for each member

def getMembers():
    stmt = (
        select(member.id,
               member.firstname,
               member.lastname,
               member.emailaddress,
               member.slackhandle)
    )
    result = executeQuery(stmt,db_engine)
    baselist = []
    for row in result.all():
        baselist.append(dict(zip(result.keys(), row)))
    return baselist


#returns one member dict for a given member ID

def getMemberByID(memberId):
    stmt = (
        select(member.id,
               member.firstname,
               member.lastname,
               member.emailaddress)
               .where(member.id == memberId)
    )
    result = executeQuery(stmt,db_engine)
    try:
        response = dict(zip(result.keys(), result.one()))
    except:
       raise ValueError("Member does not exist")
    return response