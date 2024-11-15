import json

from meshapi.util.join_records import JoinRecord

MOCK_JOIN_RECORD_PREFIX = "join-record-test"

basic_sample_join_records: dict[str, JoinRecord] = {
    f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/28/12/34/56.json": JoinRecord(
        first_name="Jon",
        last_name="Smith",
        email_address="js@gmail.com",
        phone_number="+1 585-475-2411",
        street_address="197 Prospect Place",
        city="Brooklyn",
        state="NY",
        zip_code="11238",
        apartment="1",
        roof_access=True,
        referral="Totally faked mocked join record.",
        ncl=True,
        trust_me_bro=False,
        submission_time="2024-10-28T12:34:56",
        code="500",
        replayed=0,
        install_number=None,
    ),
    f"{MOCK_JOIN_RECORD_PREFIX}/2024/10/30/12/34/57.json": JoinRecord(
        first_name="Jon",
        last_name="Smith",
        email_address="js@gmail.com",
        phone_number="+1 585-475-2411",
        street_address="711 Hudson Street",
        city="Hoboken",
        state="NJ",
        zip_code="07030",
        apartment="",
        roof_access=True,
        referral="Totally faked mocked join record.",
        ncl=True,
        trust_me_bro=False,
        submission_time="2024-10-30T12:34:57",
        code="400",
        replayed=1,
        install_number=None,
    ),
}

sample_join_record_s3_content = json.dumps(
    {
        "first_name": "Jon",
        "last_name": "Smith",
        "email_address": "js@gmail.com",
        "phone_number": "+1 585-475-2411",
        "street_address": "197 Prospect Place",
        "apartment": "1",
        "city": "Brooklyn",
        "state": "NY",
        "zip_code": "11238",
        "roof_access": True,
        "referral": "I googled it.",
        "ncl": True,
        "trust_me_bro": False,
        "code": "201",
        "replayed": 0,
        "install_number": 1002,
    }
)
