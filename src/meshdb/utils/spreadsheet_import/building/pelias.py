import logging
import re
from typing import List, Optional, Tuple

import inflect
import requests

from meshdb.utils.spreadsheet_import.building.constants import (
    DatabaseAddress,
    NormalizedAddressVariant,
)
from meshdb.utils.spreadsheet_import.building.us_state_codes import convert_state_name_to_code

PELIAS_ADDRESS_PARSER_URL = "http://10.70.178.56:6800/parser/parse"


def call_pelias_parser(address_str: str) -> List[Tuple[float, dict, dict]]:
    response = requests.get(PELIAS_ADDRESS_PARSER_URL, params={"text": address_str})
    output = []

    for solution in response.json()["solutions"]:
        components = {}
        indices = {}
        for classification in solution["classifications"]:
            label = classification["label"]
            if label in components:
                if label == "street":
                    label = "cross_street"
                else:
                    raise ValueError(
                        f"Unexpected duplicate, address "
                        f"'{address_str}' has two values for {label}: "
                        f"{components[label]} and {classification['value']}"
                    )

            # Sometimes Pelias mistakenly assumes the city is "apt" when there is no
            # city specified
            if label in ["locality", "region"] and classification["value"].lower() in [
                "apt",
                "apt.",
                "apartment",
            ]:
                continue

            components[label] = classification["value"]
            indices[label] = (classification["start"], classification["end"])

        output.append((solution["score"], components, indices))

    output.sort(key=lambda x: x[0], reverse=True)

    return output


def normalize_pelias_first_line(
    original_address: str,
    pelias_components: dict,
    pelias_indices: dict,
    variant: NormalizedAddressVariant,
) -> str:
    assert "street" in pelias_components

    if variant == NormalizedAddressVariant.OriginalFirstLine:
        # This variant is useful because sometimes the parser trips out and misses sections
        # of the address. If we're just going to write the parser output straight into the DB,
        # we don't want to be missing chunks
        for label, label_range in pelias_indices.items():
            if label not in ["housenumber", "street", "cross_street", "venue", "place"]:
                return original_address[: label_range[0]].strip(".,/- \t\n")

        # If the whole original string is only composed of housenumber, street, venue
        # and cross_street components, then just take the whole thing, it's already a first line
        return original_address.strip()

    if "cross_street" in pelias_components:
        separator = "at"
        if variant == NormalizedAddressVariant.OSMNominatim:
            separator = "&"

        assert "housenumber" not in pelias_components

        return f"{pelias_components['street']} {separator} {pelias_components['cross_street']}"

    output = ""
    if "housenumber" in pelias_components:
        output += pelias_components["housenumber"] + " "

    output += pelias_components["street"]

    return output


def pelias_to_database_address_components(
    original_address: str,
    pelias_solution: Tuple[float, dict, dict],
    variant: NormalizedAddressVariant,
) -> DatabaseAddress:
    street_address, city, state, zip_code = None, None, None, None

    confidence, components, indices = pelias_solution

    if "street" in components:
        street_address = normalize_pelias_first_line(original_address, components, indices, variant)

    if "locality" in components:
        city = components["locality"]

    if "region" in components:
        state_code = convert_state_name_to_code(components["region"])
        state = state_code or components["region"]

    if "postcode" in components:
        zip_code = components["postcode"]

    return DatabaseAddress(street_address, city, state, zip_code)


def humanify_street_address(dob_address_str: str) -> str:
    """
    Convert an address from UPPERCASE to Title Case and add ordinal indicators
    e.g. "229 EAST 13 STREET" -> "229 East 13th Street"
    This is useful making  the output of the DOB APIs more gentle

    To make sure we don't make silly mistakes like "229th East 13 Street"
    we call pelias and only add ordinal indicators to street names

    :param dob_address_str: The address (line 1 only) string to convert
    :return: A softened version of the input string
    """
    response = requests.get(PELIAS_ADDRESS_PARSER_URL, params={"text": dob_address_str})

    best_score = 0
    best_solution = None

    solution_candidates = response.json()["solutions"]
    if any(
        any(
            classification["label"] == "housenumber"
            for classification in candidate["classifications"]
        )
        for candidate in solution_candidates
    ):
        # If any of the candidates have a housenumber, then remove any candidates
        # without housenumbers. This is because sometimes the parser scores these too low,
        # but it's very important we isolate the house numbers for this operation
        solution_candidates = [
            candidate
            for candidate in solution_candidates
            if any(
                classification["label"] == "housenumber"
                for classification in candidate["classifications"]
            )
        ]

    for solution in solution_candidates:
        if solution["score"] > best_score:
            best_score = solution["score"]
            best_solution = solution

    if not best_solution:
        # If we didn't get any results trying to parse it, don't touch it. This
        # should be rare, and the occasional ALL CAPS ADDRESS won't hurt anyone
        return dob_address_str

    output_string = ""
    last_touched_orig = 0
    for classification in best_solution["classifications"]:
        if classification["label"] not in ["housenumber", "street"]:
            logging.debug(
                f"Found unexpected label {classification['label']} in "
                f"'{dob_address_str}', which is supposed to only be a first address line"
            )

        # This should really just be "street", but in some cases it mistakes words like
        # "SOUTHWEST" and "PARKWAY" as the city/state for some reason???
        if classification["label"] in ["street", "locality", "region"]:
            street_character_range = (classification["start"], classification["end"])

            street_substr = dob_address_str[street_character_range[0] : street_character_range[1]]
            street_substr_title = street_substr.title().replace("'S", "'s")

            street_substr_ordinals = ""
            last_touched_in_street = 0
            p = inflect.engine()
            for match in re.finditer(r"(\d+)\W", street_substr_title):
                street_substr_ordinals += street_substr_title[
                    last_touched_in_street : match.start(1)
                ]
                num = int(match[1])
                street_substr_ordinals += p.ordinal(num)
                last_touched_in_street = match.end(1)

            street_substr_ordinals += street_substr_title[last_touched_in_street:]

            output_string += (
                dob_address_str[last_touched_orig : street_character_range[0]].lower()
                + street_substr_ordinals
            )
            last_touched_orig = street_character_range[1]
        if classification["label"] == "housenumber":
            # Make the house "number" upper case, in case there are any letters included
            # e.g. 215A West 23rd St
            housenumber_character_range = (classification["start"], classification["end"])
            output_string += (
                dob_address_str[last_touched_orig : housenumber_character_range[0]].lower()
                + dob_address_str[
                    housenumber_character_range[0] : housenumber_character_range[1]
                ].upper()
            )
            last_touched_orig = housenumber_character_range[1]

    output_string += dob_address_str[last_touched_orig:].lower()
    return output_string
