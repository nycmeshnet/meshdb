import logging
import operator
import re
from functools import reduce
from typing import Callable, List, Optional, Tuple

import phonenumbers
from django.db.models import Q
from nameparser import HumanName

from meshapi import models
from meshapi.models import Member
from meshdb.utils.spreadsheet_import.csv_load import DroppedModification, SpreadsheetRow

BASIC_EMAIL_REGEX = re.compile(r"\S+@\S+\.\S+")

# Fix some common formatting mistakes and ease the parser's job by removing
# invalid characters
EMAIL_REPLACEMENTS = {
    "<": "",
    ">": "",
    ",": " ",
    r"\/": " ",
    "gmailcom": "gmail.com",
    r"\.\.@gmail\.com": "@gmail.com",
    r"\.\.\.": ".",
    r"\.@gmail\.com": "@gmail.com",
    r"@ gmail\.com": "@gmail.com",
    r"@@gmail\.com": "@gmail.com",
    r"@yahoo\.\.com": "@yahoo.com",
    r"&gmail\.com": "@gmail.com",
    "gmail$": "gmail.com",
    r" \.net$": ".net",
    r"\. net$": ".net",
    r" @hotmail\.com": "@hotmail.com",
    r"@ hotmail\.com": "@hotmail.com",
}


def parse_name(input_name: str) -> Tuple[Optional[str], Optional[str]]:
    parsed = HumanName(input_name)
    return parsed.first, parsed.surnames


def parse_emails(input_emails: str) -> List[str]:
    replaced_input = input_emails
    for old, new in EMAIL_REPLACEMENTS.items():
        replaced_input = re.sub(old, new, replaced_input)

    email_matches = BASIC_EMAIL_REGEX.findall(replaced_input)

    # Brian's email is often used for members / buildings where we don't have
    # an email address. This is a problem when de-duplicating using email
    # address, since we would end up consolidating all of "Brian's" entries
    # into a single member, losing name and phone number info in the process
    if "brian@nycmesh.net" in email_matches:
        email_matches.remove("brian@nycmesh.net")

    return [
        email
        for email in email_matches
        # The below check doesn't do a lot for us, because we are able to do a
        # bit of repair using the regexes, and because we have disabled all the
        # non-formatting checks.
        #
        # You might say, let's leave it enabled just in case. However, it seems
        # to filter out valid emails (for example one that contains á)
        #
        # if validate_email(
        #     primary_email_address=email,
        #     check_format=True,
        #     check_blacklist=False,  # "Evil" emails are still "valid" historical data
        #     check_dns=False,  # This is too slow
        #     check_smtp=False,  # This is too slow
        # )
    ]


def parse_phone(input_phone: str) -> Optional[phonenumbers.PhoneNumber]:
    try:
        parsed = phonenumbers.parse(input_phone, "US")
    except phonenumbers.NumberParseException:
        parsed = None

    if parsed is None or not phonenumbers.is_possible_number(parsed):
        # Try again, but trim off everything after the first " " character and
        # strip "," characters from the start and end of the remaining string
        # to get rid of notes, additional phone numbers, etc
        try:
            parsed = phonenumbers.parse(input_phone.split(" ")[0].strip(","), "US")
        except phonenumbers.NumberParseException:
            return None

    # TODO: Bring this validation to the join form
    if phonenumbers.is_possible_number(parsed):
        return parsed
    else:
        return None


def diff_new_member_against_existing(
    row_id: int,
    existing_member: models.Member,
    new_member: models.Member,
    add_dropped_edit: Callable[[DroppedModification], None],
) -> str:
    diff_notes = ""
    if existing_member.name != new_member.name and new_member.name:
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_member.installs.all()),
                row_id,
                existing_member.primary_email_address,
                "member.name",
                existing_member.name if existing_member.name else "",
                new_member.name,
            )
        )
        logging.debug(
            f"Dropping changed name from install # {row_id} " f"{repr(existing_member.name)} -> {repr(new_member.name)}"
        )
        diff_notes += f"\nDropped name change from install #{row_id}: {new_member.name}"

    if (
        existing_member.phone_number != new_member.phone_number
        and new_member.phone_number
        and existing_member.phone_number
    ):
        add_dropped_edit(
            DroppedModification(
                list(install.install_number for install in existing_member.installs.all()),
                row_id,
                existing_member.primary_email_address,
                "member.phone_number",
                existing_member.phone_number,
                new_member.phone_number,
            )
        )
        logging.debug(
            f"Dropping changed last name from install # {row_id} "
            f"{repr(existing_member.phone_number)} -> {repr(new_member.phone_number)}"
        )
        diff_notes += f"\nDropped phone number change from install #{row_id}: {new_member.phone_number}"

    return diff_notes


def get_or_create_member(
    row: SpreadsheetRow,
    add_dropped_edit: Optional[Callable[[DroppedModification], None]] = None,
) -> Tuple[models.Member, bool]:
    def nop(*args, **kwargs):
        return None

    if not add_dropped_edit:
        # Use a no-op function if our caller doesn't specify a destination
        # for dropped edits, to avoid runtime errors
        add_dropped_edit = nop

    primary_emails = parse_emails(row.email)
    stripe_emails = parse_emails(row.stripeEmail)
    secondary_emails = parse_emails(row.secondEmail)

    stripe_email = stripe_emails[0] if stripe_emails else None
    other_emails = primary_emails + secondary_emails + stripe_emails[1:]

    # Don't normally include the primary stripe email in the list of all emails,
    # however if it's the only email we've got, use it instead of having no email
    if stripe_email and not other_emails:
        other_emails = [stripe_email]

    parsed_phone = parse_phone(row.phone)

    notes = ""

    # TODO: this might actually be better in the install notes, since most of
    #  these relate to specific installs, and only some relate to contact info
    #  for the member. We should maybe talk to Olivier about this tradeoff?
    #  (also don't forget to remove the occurrence flagged below if you remove this one)
    if row.contactNotes:
        notes += f"Spreadsheet Contact Notes:\n{row.contactNotes}\n\n"

    # Keep track of garbage phone numbers just in case we're wrong about
    # their garbage-ness
    if row.phone and not parsed_phone:
        notes += f"Un-parsable Phone Number: {row.phone}\n"

    # If there were any letters in the phone number
    # (that we didn't parse into an extension)
    # it's probably a contact note like "text only".
    # Record that in the contact notes
    if re.search("[a-zA-Z]", row.phone) and parsed_phone and not parsed_phone.extension:
        notes += f"Phone Notes: {row.phone}\n"

    if row.contactNotes:
        notes += f"Spreadsheet Emails:\n{row.email}\n{row.stripeEmail}\n{row.secondEmail}\n"

    formatted_phone_number = (
        # TODO: Bring this formatting to the join form
        phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        if parsed_phone
        else None
    )

    if len(other_emails) > 0:
        existing_members = Member.objects.filter(
            reduce(
                operator.or_,
                (
                    Q(primary_email_address=email)
                    | Q(stripe_email_address=email)
                    | Q(additional_email_addresses__contains=[email])
                    for email in other_emails + ([stripe_email] if stripe_email else [])
                ),
            )
        )

        if existing_members:
            if len(existing_members) > 1:
                logging.error(
                    f"Duplicate entries detected for {other_emails[0]} at install # {row.id} "
                    f"This should not happen, these should be consolidated by a previous iteration."
                )

            diff_notes = diff_new_member_against_existing(
                row.id,
                existing_members[0],
                models.Member(
                    name=row.name,
                    phone_number=formatted_phone_number,
                ),
                add_dropped_edit,
            )

            if formatted_phone_number and not existing_members[0].phone_number:
                existing_members[0].phone_number = formatted_phone_number

            # TODO: Don't forget to remove me if we remove the previous use of contact notes above
            if row.contactNotes:
                if not existing_members[0].notes:
                    existing_members[0].notes = ""

                existing_members[0].notes += f"Spreadsheet Contact Notes:\n{row.contactNotes}\n\n"

            if diff_notes:
                if not existing_members[0].notes:
                    existing_members[0].notes = ""

                existing_members[0].notes += diff_notes

            return existing_members[0], False

    return (
        models.Member(
            name=row.name,
            primary_email_address=other_emails[0] if len(other_emails) > 0 else None,
            stripe_email_address=stripe_email,
            additional_email_addresses=other_emails[1:],
            phone_number=formatted_phone_number,
            slack_handle=None,
            notes=notes if notes else None,
        ),
        True,
    )
