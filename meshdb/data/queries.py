import stringcase
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.building import building
from ..models.install import install
from ..models.member import member
from meshdb.data.database import db, executeQuery


def getMembers(engine):
    stmt = select(
        member.id,
        member.first_name,
        member.last_name,
        member.email_address,
        member.phone_number,
        member.slack_handle,
    )
    result = executeQuery(stmt, engine)
    baselist = []
    for row in result.all():
        baselist.append(
            dict(
                zip(
                    [
                        "id",
                        "firstName",
                        "lastName",
                        "emailAddress",
                        "phoneNumber",
                        "slackHandle",
                    ],
                    row,
                )
            )
        )
    return baselist


# returns one member dict for a given member ID


def getMemberByID(engine, memberId):
    stmt = select(
        member.id,
        member.first_name,
        member.last_name,
        member.email_address,
        member.phone_number,
        member.slack_handle,
    ).where(member.id == memberId)
    result = executeQuery(stmt, engine)
    try:
        response = dict(
            zip(
                [
                    "id",
                    "firstName",
                    "lastName",
                    "emailAddress",
                    "phoneNumber",
                    "slackHandle",
                ],
                result.one(),
            )
        )
    except:
        raise ValueError("Member does not exist")
    return response


def getMemberByName(engine, firstName, lastName):
    stmt = (
        select(
            member.id,
            member.first_name,
            member.last_name,
            member.email_address,
            member.phone_number,
            member.slack_handle,
        )
        .where(member.first_name == firstName)
        .where(member.lastname == lastName)
    )
    result = executeQuery(stmt, engine)
    resultkeys = result.keys()
    resultall = result.all()
    if len(resultall) == 0:
        return False
    elif len(resultall) == 1:
        response = dict(
            zip(
                [
                    "id",
                    "firstName",
                    "lastName",
                    "emailAddress",
                    "phoneNumber",
                    "slackHandle",
                ],
                resultall[0],
            )
        )
        return response
    else:
        baselist = []
        for row in resultall:
            baselist.append(
                dict(
                    zip(
                        [
                            "id",
                            "firstName",
                            "lastName",
                            "emailAddress",
                            "phoneNumber",
                            "slackHandle",
                        ],
                        row,
                    )
                )
            )
        return baselist


def getMemberDetailsByID(engine, memberID):
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
            building.bin,
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
            building.panorama_image,
        )
        .where(member.id == memberID)
        .join(install, member.id == install.member_id)
        .join(building, install.building_id == building.id)
    )
    result = executeQuery(stmt, engine)
    try:
        response = dict(zip(result.keys(), result.one()))
    except:
        raise ValueError("Member does not exist")
    returndict = {
        "firstName": response["first_name"],
        "lastName": response["last_name"],
        "emailAddress": response["email_address"],
        "phoneNumber": response["phone_number"],
        "install": {
            "installNumber": response["building_id"],
            "status": response["install_status"],
        },
        "building": {
            "networkNumber": response["network_number"],
            "bin": response["bin"],
            "buildingStatus": response["building_status"],
            "streetAddress": response["street_address"],
            "city": response["city"],
            "state": response["state"],
            "zipCode": response["zip_code"],
            "latitude": response["latitude"],
            "longitude": response["longitude"],
            "altitude": response["altitude"],
        },
    }
    return returndict


def createNewMember(engine, input):
    newDict = {}
    for key, value in input.items():
        newDict[stringcase.snakecase(key)] = value
    newMember = member(**newDict)
    with Session(engine) as session:
        session.add_all([newMember])
        session.commit()
    return "OK"
