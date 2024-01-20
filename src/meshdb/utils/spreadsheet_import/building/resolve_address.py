import dataclasses
import logging
from typing import Callable, List, Optional, Tuple

import geopy.distance
import requests
from geopy import Location, Nominatim
from geopy.exc import GeocoderUnavailable

from meshapi.exceptions import AddressError
from meshdb.utils.spreadsheet_import.building.constants import (
    INVALID_BIN_NUMBERS,
    LOCAL_MESH_NOMINATIM_ADDR,
    NYC_BIN_LOOKUP_PREFIX,
    NYC_BIN_LOOKUP_UA,
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
        return Nominatim(domain=LOCAL_MESH_NOMINATIM_ADDR, scheme="http", timeout=5)
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
        osm_raw_addr["city"]
        if "city" in osm_raw_addr
        else osm_raw_addr["town"]
        if "town" in osm_raw_addr
        else osm_raw_addr["village"]
        if "village" in osm_raw_addr
        else None,
        osm_raw_addr["ISO3166-2-lvl4"].split("-")[1] if "ISO3166-2-lvl4" in osm_raw_addr else None,
    )


def osm_location_is_in_nyc(osm_raw_addr: dict) -> bool:
    return osm_raw_addr["country_code"] == "us" and (
        ("city" in osm_raw_addr and osm_raw_addr["city"] == "City of New York")
        or ("county" in osm_raw_addr and any(borough in osm_raw_addr["county"] for borough in NYC_COUNTIES))
    )


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
        nyc_planning_req = requests.get(f"https://geosearch.planninglabs.nyc/v2/autocomplete", params=query_params)
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
        if new_bin != spreadsheet_bin and spreadsheet_bin not in INVALID_BIN_NUMBERS:
            new_bin_lookup_response = requests.get(
                NYC_BIN_LOOKUP_PREFIX + str(new_bin),
                headers={"User-Agent": NYC_BIN_LOOKUP_UA},
            ).json()
            new_alternate_bins = (
                (new_bin_lookup_response["PropertyDetails"]["AdditionalBINsforBuilding"] or "")
                if new_bin_lookup_response["PropertyDetails"]
                else ""
            ).split(", ")
            new_bin_housenum = normalize_whitespace_and_case(
                new_bin_lookup_response["PropertyDetails"]["HouseNo"]
                if new_bin_lookup_response["PropertyDetails"]
                else ""
            )
            new_bin_street = normalize_whitespace_and_case(
                new_bin_lookup_response["PropertyDetails"]["StreetName"]
                if new_bin_lookup_response["PropertyDetails"]
                else ""
            )

            old_bin_lookup_response = requests.get(
                NYC_BIN_LOOKUP_PREFIX + str(spreadsheet_bin),
                headers={"User-Agent": NYC_BIN_LOOKUP_UA},
            ).json()
            old_alternate_bins = (
                (old_bin_lookup_response["PropertyDetails"]["AdditionalBINsforBuilding"] or "")
                if old_bin_lookup_response["PropertyDetails"]
                else ""
            ).split(", ")
            old_bin_housenum = normalize_whitespace_and_case(
                old_bin_lookup_response["PropertyDetails"]["HouseNo"]
                if old_bin_lookup_response["PropertyDetails"]
                else ""
            )
            old_bin_street = normalize_whitespace_and_case(
                old_bin_lookup_response["PropertyDetails"]["StreetName"]
                if old_bin_lookup_response["PropertyDetails"]
                else ""
            )
            old_bin_zip = normalize_whitespace_and_case(
                old_bin_lookup_response["PropertyDetails"]["Zip"] if old_bin_lookup_response["PropertyDetails"] else ""
            )

            if str(new_bin) in old_alternate_bins or str(spreadsheet_bin) in new_alternate_bins:
                # Some buildings have more than one BIN, if this explains the mismatch,
                # it's more or less impossible to tell which one we should be using, We will
                # arbitrarily pick the one we just got back since it's "more recent" and quietly
                # use that one
                output_bin = new_bin
            elif (
                old_bin_housenum != normalize_whitespace_and_case(closest_nyc_location["properties"]["housenumber"])
                or old_bin_street != normalize_whitespace_and_case(closest_nyc_location["properties"]["street"])
                or old_bin_zip != zip_code
            ):
                # The old BIN doesn't look right, maybe the spreadsheet is incorrect or out of date?
                # Let's quietly use the new BIN
                output_bin = new_bin
            else:
                # Otherwise, this is not easily explicable, warn the user about it
                # TODO: Should we flag as invalid in this case?
                logging.warning(
                    f"BIN mismatch for '{normalized_nyc_addr}'. "
                    f"Spreadsheet uses {spreadsheet_bin}, but we found {output_bin} "
                    f"for this address. We checked to see if this building has more than one BIN, "
                    f"or if the old BIN was incorrect, but couldn't explain the discrepancy "
                    f"using these methods. We're going to assume that our search was correct and "
                    f"use {output_bin} in the database."
                )

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
        if not add_dropped_edit:
            # Use a no-op function if our caller doesn't specify a destination
            # for dropped edits, to avoid runtime errors
            add_dropped_edit = lambda x: None

        row.address = row.address.strip(
            "., "  # Leading / trailing whitespace and punctuation can cause issues
            # and should never be semantically meaningful
        )

        pelias_response = call_pelias_parser(row.address)
        if not pelias_response:
            raise AddressError(f"Invalid address: '{row.address}'. No components detected")

        try:
            if pelias_response[0][0] < PELIAS_SCORE_WARNING_THRESHOLD:
                logging.debug(
                    f"Got low score of {pelias_response[0][0]} from " f"Pelias when parsing address '{row.address}'"
                )

            required_components = ["housenumber", "street"]
            if not all(component in pelias_response[0][1] for component in required_components):
                # If we didn't find a house number or street, this address is too vague
                # to parse into a specific building with OSM or the NYC Planning API,
                # Fall back to string parsing
                raise AddressError(
                    f"Invalid address: '{row.address}'. All of "
                    f"{required_components} are required and at least one is missing"
                )

            osm_db_addr = pelias_to_database_address_components(
                row.address, pelias_response[0], NormalizedAddressVariant.OSMNominatim
            )
            normalized_osm_addr = database_address_components_to_normalized_address_string(osm_db_addr)

            closest_osm_location = self._get_closest_osm_location(normalized_osm_addr, (row.latitude, row.longitude))

            if not closest_osm_location:
                raise AddressError(f"Unable to find '{row.address}' in OSM database")

            if closest_osm_location.raw["type"] in ["postcode", "administrative", "neighbourhood"]:
                # Fall back to string parsing for vague place descriptions
                raise AddressError(
                    f"Address '{row.address}' is not substantial enough to resolve " f"to a specific place"
                )

            if osm_location_is_in_nyc(closest_osm_location.raw["address"]):
                # We are in NYC, call the city planning API
                result = self._find_nyc_building(
                    row.address, pelias_response[0], (row.latitude, row.longitude), row.bin
                )
            else:
                # We are not in NYC, the best we can do is the OSM geolocation
                r_addr = closest_osm_location.raw["address"]

                for prop in ["house_number", "road", "ISO3166-2-lvl4", "postcode"]:
                    if prop not in r_addr:
                        raise AddressError(f"Invalid address '{row.address}' - {prop} not found in OSM data")

                if not any(prop in r_addr for prop in ["city", "town", "village"]):
                    raise AddressError(f"Invalid address '{row.address}' - city/town/village not found in OSM data")

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
                f"Error locating '{row.address}'. Falling back to string parsing. "
                f"Is this address valid and located in the NYC metro area?"
            )
            return self._parse_pelias_result_to_answer_and_fill_gaps_with_geocode(
                row.address,
                pelias_response[0],
                sources=[AddressTruthSource.PeliasStringParsing],
                spreadsheet_latlon=(row.latitude, row.longitude),
            )

        error_vs_google = geopy.distance.geodesic(result.discovered_lat_lon, (row.latitude, row.longitude)).m
        if error_vs_google > 200:
            add_dropped_edit(
                DroppedModification(
                    [row.id],
                    row.id,
                    result.discovered_bin if result.discovered_bin else result.address.street_address,
                    "lat_long_discrepancy_vs_spreadsheet",
                    str(result.discovered_lat_lon),
                    str((row.latitude, row.longitude)),
                )
            )
            logging.debug(
                f"Mismatch vs spreadsheet of {error_vs_google} meters for address '{row.address}'"
                f" for install # {row.id}. Wrong borough or city? We think this address is in "
                f"{result.address.city}, {result.address.state}"
            )

        return result
