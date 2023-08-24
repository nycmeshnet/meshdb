from models.building import building
from models.install import install
from models.member import member
from models.request import request
from sqlalchemy import select
import variables
from sqlalchemy.orm import Session
from db.database import create_db_engine, executeQuery
import stringcase



db_engine = create_db_engine()

# returns list of dicts for each member

def keysToCamelCase(keydict):
    

def getMembers():
    stmt = (
        select(member.id,
               member.first_name,
               member.last_name,
               member.email_address,
               member.phone_number,
               member.slack_handle)
    )
    result = executeQuery(stmt, db_engine)
    baselist = []
    for row in result.all():
        baselist.append(dict(zip(result.keys(), row)))
    return baselist


#returns one member dict for a given member ID

def getMemberByID(memberId):
    stmt = (
        select(
            member.id,
            member.first_name,
            member.last_name,
            member.email_address,
            member.phone_number,
            member.slack_handle)
            .where(member.id == memberId)
    )
    result = executeQuery(stmt,db_engine)
    try:
        response = dict(zip(result.keys(), result.one()))
    except:
       raise ValueError("Member does not exist")
    return response

def getMemberByName(firstName, lastName):
    stmt = (
            select(
            member.id,
            member.first_name,
            member.last_name,
            member.email_address,
            member.phone_number,
            member.slack_handle
        ).where(member.first_name == firstName).where(member.lastname == lastName)
    )
    result = executeQuery(stmt,db_engine)
    resultkeys = result.keys()
    resultall = result.all()
    if len(resultall) == 0:
        return False
    elif len(resultall) == 1:
        response = dict(zip(resultkeys, resultall[0]))
        return response
    else:
        baselist = []
        for row in resultall:
            baselist.append(dict(zip(resultkeys, row)))
        return baselist


def getMemberDetailsByID(memberID):
    stmt = (
        select(
            member.id,
            member.first_name,
            member.last_name,
            member.email_address,
            member.phone_number,
            member.slack_handle,
            install.install_number,
            install.building_id,
            install.install_status,
            building.street_address,
            building.building_status,
            building.city,
            building.state,
            building.zip_code,
            building.latitude,
            building.longitude,
            building.altitude,
            building.network_number,
            building.install_date,
            building.abandon_date,
            building.panorama_image
        ).where(member.id == memberID)
        .join(install, member.id == install.member_id)
        .join(building, install.building_id == building.id)
    )
    result = executeQuery(stmt, db_engine)
    try:
        response = dict(zip(result.keys(), result.one()))
    except:
        raise ValueError("Member does not exist")
    returndict = {
             'firstName': response['first_name'],
             'lastName': response['last_name'],
             'emailAddress': response['email_address'],
             'phoneNumber': response['phone_number'],
             'install': {
                 'installNumber': response['building_id'],
                 'status': response['install_status'],
                },
            'building': {
                'networkNumber': response['network_number'],
                'buildingStatus': response['building_status'],
                'streetAddress': response['street_address'],
                'city': response['city'],
                'state': response['state'],
                'zipCode': response['zip_code'],
                'latitude': response['latitude'],
                'longitude': response['longitude'],
                'altitude': response['altitude']
            }
        }
    return returndict   

def createNewMember(**kwargs):
    newMember = member
    for key, value in kwargs:
        setattr(member, key, value)
    with Session(db_engine) as session:
        session.add_all([member])
        session.commit()
    