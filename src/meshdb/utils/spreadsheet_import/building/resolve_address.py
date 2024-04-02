import logging
import re
from typing import Callable, List, Optional, Tuple

import geopy.distance
import requests
from geopy import Location, Nominatim
from geopy.exc import GeocoderUnavailable

from meshapi.exceptions import AddressError
from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS
from meshdb.utils.spreadsheet_import.building.constants import (
    INVALID_BIN_NUMBERS,
    LOCAL_MESH_NOMINATIM_ADDR,
    NYC_COUNTIES,
    OSM_CITY_SUBSTITUTIONS,
    AddressParsingResult,
    AddressTruthSource,
    DatabaseAddress,
    NormalizedAddressVariant,
)
from meshdb.utils.spreadsheet_import.building.pelias import (
    call_pelias_parser,
    humanify_street_address,
    pelias_to_database_address_components,
)
from meshdb.utils.spreadsheet_import.csv_load import DroppedModification, SpreadsheetRow

PELIAS_SCORE_WARNING_THRESHOLD = 0.5


def get_geolocator() -> Nominatim:
    try:
        requests.get(f"http://{LOCAL_MESH_NOMINATIM_ADDR}", timeout=1)
        return Nominatim(domain=LOCAL_MESH_NOMINATIM_ADDR, scheme="http", timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException:
        logging.warning("Using public OSM endpoint. Is the local OSM endpoint running?")
        return Nominatim(user_agent="andrew@nycmesh.net")


def normalize_whitespace_and_case(input_str: str) -> str:
    return " ".join(input_str.split()).lower()


def database_address_components_to_normalized_address_string(
    address: DatabaseAddress,
) -> str:
    return ", ".join(
        [
            component
            for component in [address.street_address, address.city, address.state, address.zip_code]
            if component
        ]
    )


def convert_osm_city_village_suburb_nonsense(osm_raw_addr: dict) -> Tuple[str, str]:
    if osm_location_is_in_nyc(osm_raw_addr):
        city = osm_raw_addr["suburb"]
        for old_val, new_val in OSM_CITY_SUBSTITUTIONS.items():
            city = city.replace(old_val, new_val)

        return (
            city,
            osm_raw_addr["ISO3166-2-lvl4"].split("-")[1] if "ISO3166-2-lvl4" in osm_raw_addr else None,
        )

    return (
        (
            osm_raw_addr["city"]
            if "city" in osm_raw_addr
            else (
                osm_raw_addr["town"]
                if "town" in osm_raw_addr
                else osm_raw_addr["village"]
                if "village" in osm_raw_addr
                else None
            )
        ),
        osm_raw_addr["ISO3166-2-lvl4"].split("-")[1] if "ISO3166-2-lvl4" in osm_raw_addr else None,
    )


def osm_location_is_in_nyc(osm_raw_addr: dict) -> bool:
    return osm_raw_addr["country_code"] == "us" and (
        ("city" in osm_raw_addr and osm_raw_addr["city"] == "City of New York")
        or ("county" in osm_raw_addr and any(borough in osm_raw_addr["county"] for borough in NYC_COUNTIES))
    )


def fixup_bad_address(bad_address: str) -> str:
    modified_addr = " ".join(bad_address.split())  # Multiple spaces between sections can confuse Pelias
    st_no_space_match = re.search(r"(\d+)[Ss][Tt]", modified_addr)
    if st_no_space_match:
        modified_addr = (
            modified_addr[: st_no_space_match.start(0)]
            + st_no_space_match[1]
            + " St"
            + modified_addr[st_no_space_match.end(0) :]
        )

    ave_no_space_match = re.search(r"(\d+)[Aa][Vv][Ee]", modified_addr)
    if ave_no_space_match:
        modified_addr = (
            modified_addr[: ave_no_space_match.start(0)]
            + ave_no_space_match[1]
            + " Ave"
            + modified_addr[ave_no_space_match.end(0) :]
        )

    east_west_no_space_match = re.search(r"([EeWw])(\d+)", modified_addr)
    if east_west_no_space_match:
        modified_addr = (
            modified_addr[: east_west_no_space_match.start(0)]
            + east_west_no_space_match[1]
            + " "
            + east_west_no_space_match[2]
            + modified_addr[east_west_no_space_match.end(0) :]
        )

    simple_typo_substitutions = {
        "steet": "Street",
        "avue": "Avenue",
        "concoourse": "Concourse",
        ";": ",",
        "Aveune": "Avenue",
        "nlvd": "Boulevard",
        "410 Grand": "410 Grand Street",
        "460 Grand": "460 Grand Street",
        "131 Broome": "131 Broome Street",
    }

    for typo, fix in simple_typo_substitutions.items():
        pattern = re.compile(typo, re.IGNORECASE)
        modified_addr = pattern.sub(fix, modified_addr)

    return modified_addr


class AddressParser:
    def __init__(self):
        self.geolocator = get_geolocator()

    def _parse_pelias_result_to_answer_and_fill_gaps_with_geocode(
        self,
        original_address: str,
        pelias_solution: Tuple[float, dict, dict],
        sources: List[AddressTruthSource],
        spreadsheet_latlon: Tuple[float, float],
    ) -> AddressParsingResult:
        address = pelias_to_database_address_components(
            original_address,
            pelias_solution,
            NormalizedAddressVariant.OriginalFirstLine,
        )

        if not address.city or not address.state:
            if address.zip_code:
                geo_res = self.geolocator.geocode(address.zip_code, addressdetails=True)
                if geo_res:
                    address.city, address.state = convert_osm_city_village_suburb_nonsense(geo_res.raw["address"])
                    sources.append(AddressTruthSource.OSMNominatimZIPOnly)

        # The spreadsheet lat/lon isn't authoritative, but it's a good last resort. Essentially
        # this code makes it so that we fall back to the original parsing we did with the Google
        # geocode API at the time the spreadsheet row was created
        if not address.city or not address.state or not address.zip_code:
            reverse_res = self.geolocator.reverse(spreadsheet_latlon)
            if reverse_res:
                # In theory, we could pull street address out this way also,
                # but this is so error-prone as to be misleading and nearly useless
                address.city, address.state = convert_osm_city_village_suburb_nonsense(reverse_res.raw["address"])
                if "postcode" in reverse_res.raw["address"]:
                    address.zip_code = reverse_res.raw["address"]["postcode"]

                sources.append(AddressTruthSource.ReverseGeocodeFromCoordinates)

        if address.city:
            address.city = address.city.replace("Manhattan", "New York")
            address.city = address.city.title()

        # If the state looks like a state code, uppercase it,
        # since the user might not have when they entered it originally on the form
        if address.state and len(address.state) == 2:
            address.state = address.state.upper()

        return AddressParsingResult(address, None, None, sources)

    def _get_closest_osm_location(
        self, address_str: str, spreadsheet_lat_lon: Tuple[float, float]
    ) -> Optional[Location]:
        try:
            osm_geolocation_list = self.geolocator.geocode(
                address_str,
                addressdetails=True,
                limit=10,
                exactly_one=False,
            )
        except GeocoderUnavailable:
            # We don't need a retry loop here because the geocode() function has built-in retries
            # and with our own endpoint there's no need to throttle
            logging.error(
                f"Couldn't connect to OSM API while querying for '{address_str}' "
                f"We will fall back to string parsing for this address"
            )
            return None

        if not osm_geolocation_list:
            return None

        closest_osm_location = None
        closest_distance = 99999999999999999999999999
        for osm_location in osm_geolocation_list:
            error_vs_google = geopy.distance.geodesic(
                (osm_location.latitude, osm_location.longitude), spreadsheet_lat_lon
            ).m
            if error_vs_google < closest_distance:
                closest_osm_location = osm_location
                closest_distance = error_vs_google

        return closest_osm_location

    def _find_nyc_building(
        self,
        original_addr_string: str,
        pelias_response: Tuple[float, dict, dict],
        spreadsheet_lat_lon: Tuple[float, float],
        spreadsheet_bin: Optional[int],
    ):
        nyc_db_addr = pelias_to_database_address_components(
            original_addr_string, pelias_response, NormalizedAddressVariant.PeliasNYCPlanningLabs
        )
        normalized_nyc_addr = database_address_components_to_normalized_address_string(nyc_db_addr)

        query_params = {"text": normalized_nyc_addr, "size": 10}

        # Empirically, the /autocomplete endpoint performs better than the /search endpoint
        # (don't ask me why)
        nyc_planning_req = requests.get(
            "https://geosearch.planninglabs.nyc/v2/autocomplete",
            params=query_params,
            timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS,
        )
        nyc_planning_resp = nyc_planning_req.json()

        closest_nyc_location = None
        closest_distance = 99999999999999999999999999
        for nyc_planning_location in nyc_planning_resp["features"]:
            error_vs_google = geopy.distance.geodesic(
                (
                    reversed(nyc_planning_location["geometry"]["coordinates"])
                ),  # Strange GIS nonsense, this is [long, lat] formatted
                spreadsheet_lat_lon,
            ).m

            # Discard results with bad BIN values
            if int(nyc_planning_location["properties"]["addendum"]["pad"]["bin"]) in INVALID_BIN_NUMBERS:
                continue

            # Look for an exact BIN match and use that if available
            if int(nyc_planning_location["properties"]["addendum"]["pad"]["bin"]) == spreadsheet_bin:
                closest_distance = error_vs_google
                closest_nyc_location = nyc_planning_location
                break

            # Otherwise look for the closest distance based on lat/lon
            if error_vs_google < closest_distance:
                closest_nyc_location = nyc_planning_location
                closest_distance = error_vs_google

        if closest_nyc_location is None:
            raise AddressError(f"Could not find '{normalized_nyc_addr}' in NYC Planning DB")

        for prop in ["housenumber", "borough", "region", "postalcode"]:
            if prop not in closest_nyc_location["properties"]:
                raise AddressError(f"Invalid address {normalized_nyc_addr} - {prop} not found in NYC Planning data")

        street_address = (
            f"{closest_nyc_location['properties']['housenumber']} {closest_nyc_location['properties']['street']}"
        )
        street_address = humanify_street_address(street_address.replace("B'WAY", "BROADWAY"))
        city = closest_nyc_location["properties"]["borough"].replace("Manhattan", "New York")
        state = closest_nyc_location["properties"][
            "region_a"
        ]  # I think this is some euro-centric GIS standard?? (they call state "region")
        zip_code = closest_nyc_location["properties"]["postalcode"]
        new_lon, new_lat = closest_nyc_location["geometry"][
            "coordinates"
        ]  # Strange GIS nonsense, this is [long, lat] formatted
        new_bin = int(closest_nyc_location["properties"]["addendum"]["pad"]["bin"])

        if normalize_whitespace_and_case(
            closest_nyc_location["properties"]["housenumber"]
        ) != normalize_whitespace_and_case(
            pelias_response[1]["housenumber"]
            # We'd like to check street name here also, but it's very difficult to normalize
            # ) or normalize_whitespace_and_case(
            #     closest_nyc_location["properties"]["street"]
            # ) != normalize_whitespace_and_case(
            #     pelias_response[1]["street"]
        ):
            # If the address doesn't seem right, fall back to string parsing
            raise AddressError(
                f"Got a bad response back from the NYC planning API. Discovered address:"
                f" {street_address} does not match search address {normalized_nyc_addr}"
            )

        output_bin = new_bin

        return AddressParsingResult(
            address=DatabaseAddress(street_address, city, state, zip_code),
            discovered_bin=output_bin,
            discovered_lat_lon=(new_lat, new_lon),
            truth_sources=[AddressTruthSource.NYCPlanningLabs],
        )

    def parse_address(
        self,
        row: SpreadsheetRow,
        add_dropped_edit: Optional[Callable[[DroppedModification], None]] = None,
    ) -> AddressParsingResult:
        def nop(*args, **kwargs):
            return None

        if not add_dropped_edit:
            # Use a no-op function if our caller doesn't specify a destination
            # for dropped edits, to avoid runtime errors
            add_dropped_edit = nop

        input_address = row.address.strip(
            "., "  # Leading / trailing whitespace and punctuation can cause issues
            # and should never be semantically meaningful
        )

        pelias_response = call_pelias_parser(input_address)
        if not pelias_response:
            logging.warning(f"Detected invalid address '{input_address}'. Trying some common substitutions to fix it")
            input_address = fixup_bad_address(input_address)
            pelias_response = call_pelias_parser(input_address)
            if not pelias_response:
                raise AddressError(
                    f"Invalid address: '{input_address}'. No components detected, even after attempting fixes"
                )

        try:
            if pelias_response[0][0] < PELIAS_SCORE_WARNING_THRESHOLD:
                logging.debug(
                    f"Got low score of {pelias_response[0][0]} from " f"Pelias when parsing address '{input_address}'"
                )

            required_components = ["housenumber", "street"]
            if not all(component in pelias_response[0][1] for component in required_components):
                # If we didn't find a house number or street, this address is too vague
                # to parse into a specific building with OSM or the NYC Planning API,
                # Fall back to string parsing
                raise AddressError(
                    f"Invalid address: '{input_address}'. All of "
                    f"{required_components} are required and at least one is missing"
                )

            osm_db_addr = pelias_to_database_address_components(
                input_address, pelias_response[0], NormalizedAddressVariant.OSMNominatim
            )
            normalized_osm_addr = database_address_components_to_normalized_address_string(osm_db_addr)

            closest_osm_location = self._get_closest_osm_location(normalized_osm_addr, (row.latitude, row.longitude))

            if not closest_osm_location:
                raise AddressError(f"Unable to find '{input_address}' in OSM database")

            if closest_osm_location.raw["type"] in ["postcode", "administrative", "neighbourhood"]:
                # Fall back to string parsing for vague place descriptions
                raise AddressError(
                    f"Address '{input_address}' is not substantial enough to resolve to a specific place"
                )

            if osm_location_is_in_nyc(closest_osm_location.raw["address"]):
                # We are in NYC, call the city planning API
                result = self._find_nyc_building(
                    input_address, pelias_response[0], (row.latitude, row.longitude), row.bin
                )
            else:
                # We are not in NYC, the best we can do is the OSM geolocation
                r_addr = closest_osm_location.raw["address"]

                for prop in ["house_number", "road", "ISO3166-2-lvl4", "postcode"]:
                    if prop not in r_addr:
                        raise AddressError(f"Invalid address '{input_address}' - {prop} not found in OSM data")

                if not any(prop in r_addr for prop in ["city", "town", "village"]):
                    raise AddressError(f"Invalid address '{input_address}' - city/town/village not found in OSM data")

                city, state = convert_osm_city_village_suburb_nonsense(r_addr)

                result = AddressParsingResult(
                    address=DatabaseAddress(
                        street_address=f"{r_addr['house_number']} {r_addr['road']}",
                        city=city,
                        state=state,
                        zip_code=r_addr["postcode"],
                    ),
                    discovered_bin=None,
                    discovered_lat_lon=(
                        closest_osm_location.latitude,
                        closest_osm_location.longitude,
                    ),
                    truth_sources=[AddressTruthSource.OSMNominatim],
                )
        except AddressError:
            logging.debug(
                f"Error locating '{input_address}'. Falling back to string parsing. "
                f"Is this address valid and located in the NYC metro area?"
            )
            return self._parse_pelias_result_to_answer_and_fill_gaps_with_geocode(
                input_address,
                pelias_response[0],
                sources=[AddressTruthSource.PeliasStringParsing],
                spreadsheet_latlon=(row.latitude, row.longitude),
            )

        return result
