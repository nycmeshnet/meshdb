class MeshDBError(Exception):
    pass


# Used in Validation to warn of an invalid address
class AddressError(MeshDBError):
    pass

class UnsupportedAddressError(MeshDBError):
    pass

# Used in Validation to warn that one of the APIs we depend on might be
# borked.
class AddressAPIError(MeshDBError):
    pass


# Used when something goes wrong with NYC Open Data
class OpenDataAPIError(MeshDBError):
    pass
