from meshapi.models import Device, Install, Node

sample_member = {
    "name": "John Smith",
    "primary_email_address": "john.smith@example.com",
    "phone_number": "+1 555-555-5555",
    "slack_handle": "@jsmith",
}

sample_building = {
    "bin": 8888,
    "street_address": "3333 Chom St",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": "11111",
    "latitude": 0.0,
    "longitude": 0.0,
    "altitude": 0.0,
    "address_truth_sources": ["NYCPlanningLabs"],
}


sample_node = {
    "name": "Amazing Node",
    "status": Node.NodeStatus.ACTIVE,
    "latitude": 0.0,
    "longitude": 0.0,
}

sample_device = {
    "status": Device.DeviceStatus.ACTIVE,
}

sample_install = {
    "status": Install.InstallStatus.ACTIVE,
    "ticket_number": "69",
    "request_date": "2022-02-27T00:00:00Z",
    "install_date": "2022-03-01",
    "abandon_date": "9999-01-01",
    "unit": "3",
    "roof_access": True,
    "notes": "Referral: Read about it on the internet",
    "stripe_subscription_id": "sub_NotARealIDValue",
}

sample_address_response = {
    "features": [
        {
            "geometry": {"coordinates": [-73.98492, 40.716245]},
            "properties": {
                "postalcode": 10002,
                "housenumber": "151",
                "street": "Broome St",
                "borough": "Manhattan",
                "region_a": "NY",
                "addendum": {"pad": {"bin": 1234}},
            },
        }
    ]
}

uisp_devices = [
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid1",
            "name": "nycmesh-1234-dev1",
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": None,
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid2",
            "name": "nycmesh-5678-dev2",
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": "inactive",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid3",
            "name": "nycmesh-7012-dev3",
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid9",
            "name": "nycmesh-1234-dev9",
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "ap-ptmp",
        },
        "identification": {
            "id": "uisp-uuid99",
            "name": "nycmesh-1234-east",
            "model": "LAP-120",
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid5",
            "name": "nycmesh-7777-abc",
            "category": "optical",  # Causes it to be excluded
        },
    },
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid5",
            "name": "nycmesh-abc-def",  # Causes it to be excluded, no NN
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "sta-ptmp",
        },
        "identification": {
            "id": "uisp-uuid5",
            "name": "nycmesh-888-def",  # Causes it to be excluded, no NN 888 in the DB
            "category": "wireless",
            "type": "airMax",
        },
    },
    {
        "overview": {
            "status": "active",
            "createdAt": "2018-11-14T15:20:32.004Z",
            "lastSeen": "2024-08-12T02:04:35.335Z",
            "wirelessMode": "ap-ptmp",
        },
        "identification": {
            "id": "uisp-uuid999",
            "name": "nycmesh-1234-northsouth",  # this direction makes no sense, causes guess of 0 deg
            "model": "LAP-120",
            "category": "wireless",
            "type": "airMax",
        },
    },
]

uisp_links = [
    {
        "from": {
            "device": {
                "identification": {
                    "id": "uisp-uuid1",
                    "category": "wireless",
                    "name": "nycmesh-1234-dev1",
                }
            }
        },
        "to": {
            "device": {
                "identification": {
                    "id": "uisp-uuid2",
                    "category": "wireless",
                    "name": "nycmesh-5678-dev2",
                }
            }
        },
        "state": "active",
        "id": "uisp-uuid1",
        "type": "wireless",
        "frequency": 5_000,
    },
    {
        "from": {
            "device": {
                "identification": {
                    "id": "uisp-uuid1",
                    "category": "wireless",
                    "name": "nycmesh-1234-dev1",
                }
            }
        },
        "to": {
            "device": {
                "identification": {
                    "id": "uisp-uuid3",
                    "category": "wireless",
                    "name": "nycmesh-7012-dev3",
                }
            }
        },
        "state": "inactive",
        "id": "uisp-uuid2",
        "type": "wireless",
        "frequency": 60_000,
    },
    {
        "from": {
            "device": {
                "identification": {
                    "id": "uisp-uuid2",
                    "category": "wireless",
                    "name": "nycmesh-5678-dev2",
                }
            }
        },
        "to": {
            "device": {
                "identification": {
                    "id": "uisp-uuid4",
                    "category": "wireless",
                    "name": "nycmesh-7890-dev4",
                }
            }
        },
        "state": "active",
        "id": "uisp-uuid3",
        "type": "wireless",
        "frequency": 5_000,
    },
    {
        "from": {
            "device": {
                "identification": {
                    "id": "uisp-uuid2",
                    "category": "wireless",
                    "name": "nycmesh-5678-dev2",
                }
            }
        },
        "to": {
            "device": {
                "identification": {
                    "id": "uisp-uuid-non-existent",  # Causes this link to be excluded
                    "category": "wireless",
                    "name": "nycmesh-3456-dev4",
                }
            }
        },
        "state": "active",
        "id": "uisp-uuid4",
        "type": "wireless",
        "frequency": 5_000,
    },
    {
        "from": {
            "device": {
                "identification": {
                    "id": "uisp-uuid-non-existent",  # Causes this link to be excluded
                    "category": "wireless",
                    "name": "nycmesh-5678-dev2",
                }
            }
        },
        "to": {
            "device": {
                "identification": {
                    "id": "uisp-uuid3",
                    "category": "wireless",
                    "name": "nycmesh-7012-dev3",
                }
            }
        },
        "state": "active",
        "id": "uisp-uuid4",
        "type": "wireless",
        "frequency": 5_000,
    },
    {
        "from": {
            "device": {
                "identification": {
                    "id": "uisp-uuid1",
                    "category": "wireless",
                    "name": "nycmesh-1234-dev1",
                }
            }
        },
        "to": {
            "device": {
                "identification": {
                    "id": "uisp-uuid4",
                    "category": "wireless",
                    "name": "nycmesh-3456-dev4",
                }
            }
        },
        "state": "active",
        "id": "uisp-uuid5",
        "type": "ethernet",
    },
]
