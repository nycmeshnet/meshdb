valid_join_form_submission = {
    "first_name": "John",
    "last_name": "Smith",
    "email": "jsmith@gmail.com",
    "phone": "+1585-758-3425",  # CSH's phone number :P
    "street_address": "151 Broome St",
    "city": "New York",
    "state": "NY",
    "zip": 10002,
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
}

bad_phone_join_form_submission = {
    "first_name": "John",
    "last_name": "Smith",
    "email": "jsmith@gmail.com",
    "phone": "555-555-5555",
    "street_address": "151 Broome St",
    "city": "New York",
    "state": "NY",
    "zip": 10002,
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
}

invalid_join_form_submission = {
    "first_name": 25,
    "last_name": 69,
    "email": 420,
    "phone": "eight",
    "street_address": False,
    "city": True,
    "state": "NY",
    "zip": 11215,
    "apartment": 3,
    "roof_access": True,
}
