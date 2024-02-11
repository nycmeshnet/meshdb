from meshdb.utils.spreadsheet_import.building.resolve_address import call_pelias_parser, fixup_bad_address


def test_fixup():
    assert fixup_bad_address("244 E 45st New York") == "244 E 45 St New York"
    assert fixup_bad_address("244 E 45St New York") == "244 E 45 St New York"
    assert fixup_bad_address("244 E 45ST New York") == "244 E 45 St New York"
    assert fixup_bad_address("244 E 45 St New York") == "244 E 45 St New York"

    assert fixup_bad_address("244 5Ave New York") == "244 5 Ave New York"
    assert fixup_bad_address("244 5AVE New York") == "244 5 Ave New York"
    assert fixup_bad_address("244 5 Ave New York") == "244 5 Ave New York"

    assert fixup_bad_address("357 13th Steet Apt #2") == "357 13th Street Apt #2"
    assert fixup_bad_address("357 13th STEET Apt #2") == "357 13th Street Apt #2"
    assert fixup_bad_address("357 13th steet Apt #2") == "357 13th Street Apt #2"

    assert fixup_bad_address("357 6th Avue") == "357 6th Avenue"
    assert fixup_bad_address("357 6th steet") == "357 6th Street"
    assert fixup_bad_address("357 Grand concoourse") == "357 Grand Concourse"

    assert fixup_bad_address("244 E45 St New York") == "244 E 45 St New York"
    assert fixup_bad_address("244 e45St New York") == "244 e 45 St New York"
    assert fixup_bad_address("244 W45St New York") == "244 W 45 St New York"

    assert fixup_bad_address("244 Abc nlvd New York") == "244 Abc Boulevard New York"

    assert fixup_bad_address("244   W 45St    New York") == "244 W 45 St New York"
    assert fixup_bad_address("244   W 45St    New York; 10023") == "244 W 45 St New York, 10023"


def test_pelias_bowery():
    # If this is failing, it's probably because you don't have connectivity
    # to a pelias parser, maybe you need to run it with Docker?

    result = call_pelias_parser("123 Bowery, New York, NY")
    assert result[0][1] == {"housenumber": "123", "locality": "New York", "region": "NY", "street": "Bowery"}
    assert result[0][2] == {"housenumber": (0, 3), "locality": (12, 20), "region": (22, 24), "street": (4, 10)}

    result = call_pelias_parser("123 Bowery")
    assert result[0][1] == {"housenumber": "123", "street": "Bowery"}
    assert result[0][2] == {"housenumber": (0, 3), "street": (4, 10)}
