from meshdb.utils.spreadsheet_import.building.pelias import humanify_street_address


def test_example_addresses():
    assert humanify_street_address("89 BAXTER STREET") == "89 Baxter Street"
    assert humanify_street_address("7210 5 AVENUE") == "7210 5th Avenue"
    assert humanify_street_address("2317 EAST 71 STREET") == "2317 East 71st Street"
    assert humanify_street_address("123 EAST 14 STREET") == "123 East 14th Street"
    assert humanify_street_address("443 WEST 22 STREET") == "443 West 22nd Street"
    assert humanify_street_address("2975 GRAND CONCOURSE") == "2975 Grand Concourse"
    assert humanify_street_address("23 ST. MARK'S PLACE") == "23 St. Mark's Place"

    assert humanify_street_address("5 AVENUE AT 34 STREET") == "5th Avenue at 34th Street"
    assert humanify_street_address("AMSTERDAM AVENUE AT 89 STREET") == "Amsterdam Avenue at 89th Street"

    assert humanify_street_address("30-02 WHITESTONE EXPRESSWAY WEST SR") == "30-02 Whitestone Expressway West Sr"
    assert humanify_street_address("88 PROSPECT PARK SOUTHWEST") == "88 Prospect Park Southwest"
    assert humanify_street_address("246 BAY RIDGE PARKWAY") == "246 Bay Ridge Parkway"

    assert humanify_street_address("8602 RIDGE BOULEVARD") == "8602 Ridge Boulevard"
    assert humanify_street_address("34324 STREET AT 3 AVENUE") == "34324th Street at 3rd Avenue"
    assert humanify_street_address("34324 ST AT 3 AV") == "34324th St at 3rd Av"
    assert humanify_street_address("RIDGE BOULEVARD AT 6 AVENUE") == "Ridge Boulevard at 6th Avenue"

    assert humanify_street_address("580G GRAND STREET") == "580G Grand Street"
    assert humanify_street_address("215A WEST 23 ST") == "215A West 23rd St"
