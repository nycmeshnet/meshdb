import logging
import os
import re

import inflect
import requests
from meshdb.environment import PELIAS_ADDRESS_PARSER_URL

from meshapi.util.constants import DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS
from meshdb import environment



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
    response = requests.get(
        PELIAS_ADDRESS_PARSER_URL, params={"text": dob_address_str}, timeout=DEFAULT_EXTERNAL_API_TIMEOUT_SECONDS
    )

    best_score = 0
    best_solution = None

    solution_candidates = response.json()["solutions"]
    if any(
        any(classification["label"] == "housenumber" for classification in candidate["classifications"])
        for candidate in solution_candidates
    ):
        # If any of the candidates have a housenumber, then remove any candidates
        # without housenumbers. This is because sometimes the parser scores these too low,
        # but it's very important we isolate the house numbers for this operation
        solution_candidates = [
            candidate
            for candidate in solution_candidates
            if any(classification["label"] == "housenumber" for classification in candidate["classifications"])
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
                street_substr_ordinals += street_substr_title[last_touched_in_street : match.start(1)]
                street_substr_ordinals += p.ordinal(match[1])
                last_touched_in_street = match.end(1)

            street_substr_ordinals += street_substr_title[last_touched_in_street:]

            output_string += (
                dob_address_str[last_touched_orig : street_character_range[0]].lower() + street_substr_ordinals
            )
            last_touched_orig = street_character_range[1]
        if classification["label"] == "housenumber":
            # Make the house "number" upper case, in case there are any letters included
            # e.g. 215A West 23rd St
            housenumber_character_range = (classification["start"], classification["end"])
            output_string += (
                dob_address_str[last_touched_orig : housenumber_character_range[0]].lower()
                + dob_address_str[housenumber_character_range[0] : housenumber_character_range[1]].upper()
            )
            last_touched_orig = housenumber_character_range[1]

    output_string += dob_address_str[last_touched_orig:].lower()
    return output_string
