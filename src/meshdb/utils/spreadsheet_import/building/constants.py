import dataclasses
from enum import Enum
from typing import List, Optional, Tuple

LOCAL_MESH_NOMINATIM_ADDR = "10.70.178.53:8080"
INVALID_BIN_NUMBERS = [-2, -1, 0, 1000000, 2000000, 3000000, 4000000]

NYC_BIN_LOOKUP_PREFIX = (
    "https://a810-dobnow.nyc.gov/Publish/WrapperPP/PublicPortal.svc/getPublicPortalPropertyDetailsGet/2%7C"
)
# This API is private, and doesn't respond to us if we don't pretend to be a browser-based client
# We don't need this API for high volume / frequency, we should blend into the browser traffic
NYC_BIN_LOOKUP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

NYC_COUNTIES = [
    "New York County",
    "Kings County",
    "Queens County",
    "Bronx County",
    "Richmond County",
]

OSM_CITY_SUBSTITUTIONS = {
    "Queens County": "Queens",
    "Kings County": "Brooklyn",
    "Richmond County": "Staten Island",
    "Bronx County": "Bronx",
    "The Bronx": "Bronx",
    "New York County": "New York",
    "Manhattan": "New York",
}

QUEENS_NEIGHBORHOODS = {
    "elmhurst",
    "garden city park",
    "glen oaks",
    "s floral park",
    "cambria heights",
    "la guardia airport",
    "saint albans",
    "cambria hts",
    "glendale",
    "kew garden hl",
    "corona",
    "hillside mnr",
    "hillside manor",
    "manhasset hl",
    "auburndale",
    "east elmhurst",
    "laurelton",
    "north new hyde park",
    "fresh meadows",
    "north hills",
    "woodside",
    "bayside",
    "bellerose village",
    "jackson heights",
    "la gurda arpt",
    "maspeth",
    "n new hyde pk",
    "south floral park",
    "oakland gdns",
    "sprngfld gdns",
    "middle vlg",
    "oakland gardens",
    "bayside hills",
    "jamaica",
    "sunnyside",
    "college point",
    "floral park",
    "ozone park",
    "kew gardens",
    "springfield gardens",
    "whitestone",
    "douglaston",
    "long is city",
    "howard beach",
    "jackson hts",
    "malba",
    "new hyde park",
    "flushing",
    "bellerose vlg",
    "manhasset hills",
    "kew gardens hills",
    "rosedale",
    "astoria",
    "beechhurst",
    "little neck",
    "middle village",
    "rego park",
    "hollis hills",
    "long island city",
    "forest hills",
    "ridgewood",
    "garden cty pk",
}


class NormalizedAddressVariant(Enum):
    OSMNominatim = "OSMNominatim"
    PeliasNYCPlanningLabs = "PeliasNYCPlanningLabs"
    OriginalFirstLine = "OriginalFirstLine"


class AddressTruthSource(Enum):
    OSMNominatim = "OSMNominatim"
    OSMNominatimZIPOnly = "OSMNominatimZIPOnly"
    NYCPlanningLabs = "NYCPlanningLabs"
    PeliasStringParsing = "PeliasStringParsing"
    ReverseGeocodeFromCoordinates = "ReverseGeocodeFromCoordinates"
    HumanEntry = "HumanEntry"


@dataclasses.dataclass
class DatabaseAddress:
    street_address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]

    def is_valid(self) -> bool:
        return (
            self.street_address is not None
            and self.city is not None
            and self.state is not None
            and self.zip_code is not None
        )


@dataclasses.dataclass
class AddressParsingResult:
    address: DatabaseAddress
    discovered_bin: Optional[int]
    discovered_lat_lon: Optional[Tuple[float, float]]
    truth_sources: List[AddressTruthSource]
