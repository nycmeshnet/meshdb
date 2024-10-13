valid_join_form_submission = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "jsmith@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "151 Broome Street",  # Also covers New York County Test Case
    "parsed_street_address": "151 Broome Street",
    "city": "New York",
    "state": "NY",
    "zip_code": "10002",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "151",
                    "street": "Broome Street",
                    "borough": "New York",
                    "region_a": "NY",
                    "postalcode": "10002",
                    "addendum": {"pad": {"bin": 1077609}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

# Join form submission, but the phone and the address are going to be corrected
# by us and the member needs to confirm that
valid_join_form_submission_needs_expansion = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "jsmith@gmail.com",
    "phone_number": "+1585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "151 Broome St",  # Also covers New York County Test Case
    "parsed_street_address": "151 Broome Street",
    "city": "New York",
    "state": "NY",
    "zip_code": "10002",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": False,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "151",
                    "street": "Broome Street",
                    "borough": "New York",
                    "region_a": "NY",
                    "postalcode": "10002",
                    "addendum": {"pad": {"bin": 1077609}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

valid_join_form_submission_city_needs_expansion = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "jsmith@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "151 Broome Street",  # Also covers New York County Test Case
    "parsed_street_address": "151 Broome Street",
    "city": "Manhattan",
    "parsed_city": "New York",
    "state": "NY",
    "zip_code": "10002",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "151",
                    "street": "Broome Street",
                    "borough": "New York",
                    "region_a": "NY",
                    "postalcode": "10002",
                    "addendum": {"pad": {"bin": 1077609}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

valid_join_form_submission_street_needs_expansion = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "jsmith@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "151 broome st",  # Also covers New York County Test Case
    "parsed_street_address": "151 Broome Street",
    "city": "Manhattan",
    "parsed_city": "New York",
    "state": "NY",
    "zip_code": "10002",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "151",
                    "street": "Broome Street",
                    "borough": "New York",
                    "region_a": "NY",
                    "postalcode": "10002",
                    "addendum": {"pad": {"bin": 1077609}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

valid_join_form_submission_with_apartment_in_address = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "jsmith@gmail.com",
    "phone_number": "+1 585-758-3425",
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "151 Broome St, Apt 1B",  # Apt shouldn't be here, but this example tests robustness
    "parsed_street_address": "151 Broome Street",
    "city": "New York",
    "state": "NY",
    "zip_code": "10002",
    "apartment": "Apt 1B",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "151",
                    "street": "Broome Street",
                    "borough": "New York",
                    "region_a": "NY",
                    "postalcode": "10002",
                    "addendum": {"pad": {"bin": 1077609}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

valid_join_form_submission_no_email = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": None,
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "151 Broome St",  # Also covers New York County Test Case
    "parsed_street_address": "151 Broome Street",
    "city": "New York",
    "state": "NY",
    "zip_code": "10002",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "151",
                    "street": "Broome Street",
                    "borough": "New York",
                    "region_a": "NY",
                    "postalcode": "10002",
                    "addendum": {"pad": {"bin": 1077609}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

richmond_join_form_submission = {
    "first_name": "Maya",
    "last_name": "Viernes",
    "email_address": "maya.viernes@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "475 Seaview Ave",
    "parsed_street_address": "475 Seaview Avenue",
    "city": "Staten Island",
    "state": "NY",
    "zip_code": "10305",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "475",
                    "street": "Seaview Avenue",
                    "borough": "Staten Island",
                    "region_a": "NY",
                    "postalcode": "10305",
                    "addendum": {"pad": {"bin": 123456}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

kings_join_form_submission = {
    "first_name": "Anna",
    "last_name": "Edwards",
    "email_address": "aedwards@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "188 Prospect Park W",
    "parsed_street_address": "188 Prospect Park West",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": "11215",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "188",
                    "street": "Prospect Park West",
                    "borough": "Brooklyn",
                    "region_a": "NY",
                    "postalcode": "11215",
                    "addendum": {"pad": {"bin": 123456}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

queens_join_form_submission = {
    "first_name": "Lee",
    "last_name": "Cho",
    "email_address": "lcho@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "36-01 35th Ave",
    "parsed_street_address": "36-01 35th Avenue",
    "city": "Queens",
    "state": "NY",
    "zip_code": "11106",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "36-01",
                    "street": "35 Avenue",
                    "borough": "Queens",
                    "region_a": "NY",
                    "postalcode": "11106",
                    "addendum": {"pad": {"bin": 123456}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

bronx_join_form_submission = {
    "first_name": "Richie",
    "last_name": "Smith",
    "email_address": "rsmith@gmail.com",
    "phone_number": "+1 585-758-3425",  # CSH's phone number :P
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "250 Bedford Park Blvd W",
    "parsed_street_address": "250 Bedford Park Blvd West",
    "city": "Bronx",
    "state": "NY",
    "zip_code": "10468",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "250",
                    "street": "Bedford Park Blvd West",
                    "borough": "Bronx",
                    "region_a": "NY",
                    "postalcode": "10468",
                    "addendum": {"pad": {"bin": 123456}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}

non_nyc_join_form_submission = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email_address": "jdoe@gmail.com",
    "phone_number": "+1 585-758-3425",
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "480 E Broad St",
    "parsed_street_address": "480 East Broad Street",
    "city": "Columbus",
    "state": "OH",
    "zip_code": "43215",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {"features": []},
}

new_jersey_join_form_submission = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email_address": "jdoe@gmail.com",
    "phone_number": "+1 585-758-3425",
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "711 Hudson St",
    "parsed_street_address": "711 Hudson Street",
    "city": "Hoboken",
    "state": "NJ",
    "zip_code": "07030",
    "apartment": "",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {"features": []},
}

invalid_join_form_submission = {
    "first_name": 25,
    "last_name": 69,
    "email_address": 420,
    "phone_number": "eight",
    "street_address": False,
    "parsed_street_address": False,
    "city": True,
    "state": "NY",
    "zip_code": "11215",
    "apartment": 3,
    "roof_access": True,
    "ncl": "a duck",
    "trust_me_bro": True,
    "dob_addr_response": {"features": []},
}


jefferson_join_form_submission = {
    "first_name": "John",
    "last_name": "Smith",
    "email_address": "jsmith@gmail.com",
    "phone_number": "+1 585-758-3425",
    "parsed_phone": "+1 585-758-3425",  # CSH's phone number :P
    "street_address": "476 Jefferson Street",
    "parsed_street_address": "476 Jefferson Street",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": "11237",
    "apartment": "27",
    "roof_access": True,
    "referral": "Googled it or something IDK",
    "ncl": True,
    "trust_me_bro": True,
    "dob_addr_response": {
        "features": [
            {
                "properties": {
                    "housenumber": "476",
                    "street": "Jefferson Street",
                    "borough": "Brooklyn",
                    "region_a": "NY",
                    "postalcode": "11237",
                    "addendum": {"pad": {"bin": 123456}},
                },
                "geometry": {"coordinates": [0, 0]},
            }
        ]
    },
}
