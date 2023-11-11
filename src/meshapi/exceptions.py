class MeshDBError(Exception):
    pass


# Used in Validation to warn of an invalid address
class AddressError(MeshDBError):
    pass


# Used in Validation to warn that one of the APIs we depend on might be
# borked.
class AddressAPIError(MeshDBError):
    pass
