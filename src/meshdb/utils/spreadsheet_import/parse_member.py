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

FAKE_PHONE_NUMBERS = ["+1 999-999-9999", "+1 333-333-3333"]


def merge_member_objects(members: List[Member]) -> Member:
    if len(members) == 0:
        raise ValueError("members list is empty")

    if len(members) == 1:
        return members[0]

    merged_member = Member(
        name=None,
        primary_email_address=None,
        stripe_email_address=None,
        additional_email_addresses=[],
        phone_number=None,
        additional_phone_numbers=[],
        slack_handle=None,
        notes="",
    )

    # Sort by ID so that earlier spreadsheet rows take precedence over earlier ones
    members.sort(key=lambda m: m.id)

    # Merge many members down into one
    for member in members:
        if merged_member.name is None:
            merged_member.name = member.name
        else:
            if merged_member.name != member.name and member.name:
                # TODO: Fix tracking for this?
                # add_dropped_edit(
                #     DroppedModification(
                #         list(install.install_number for install in existing_member.installs.all()),
                #         row_id,
                #         row_status,
                #         existing_member.primary_email_address,
                #         "member.name",
                #         existing_member.name if existing_member.name else "",
                #         new_member.name,
                #     )
                # )
                installs = [i.install_number for i in member.installs.all()]
                logging.info(
                    f"Dropping name change {repr(merged_member.name)} -> {repr(member.name)} "
                    f"for member id {members[0].id}"
                )
                merged_member.notes += f"\nDropped name change: {member.name}"

        if merged_member.primary_email_address is None:
            merged_member.primary_email_address = member.primary_email_address
        if merged_member.stripe_email_address is None:
            merged_member.stripe_email_address = member.stripe_email_address

        for email in [member.primary_email_address, member.stripe_email_address] + member.additional_email_addresses:
            if (
                email
                and email
                not in [
                    merged_member.primary_email_address,
                    merged_member.stripe_email_address,
                ]
                + merged_member.additional_email_addresses
            ):
                merged_member.additional_email_addresses.append(email)

        if merged_member.phone_number is None:
            merged_member.phone_number = member.phone_number

        for phone_number in [member.phone_number] + member.additional_phone_numbers:
            if (
                phone_number
                and phone_number not in [merged_member.phone_number] + merged_member.additional_phone_numbers
            ):
                merged_member.additional_phone_numbers.append(phone_number)

        if merged_member.slack_handle is None:
            merged_member.slack_handle = member.slack_handle

        if member.notes:
            merged_member.notes += member.notes

    merged_member.save()

    for member in members:
        for install in member.installs.all():
            merged_member.installs.add(install)

    return merged_member


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

    # Do the same thing for other fake emails used for similar situations
    if "noclientemail@gsg.com" in email_matches:
        email_matches.remove("noclientemail@gsg.com")

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

    if formatted_phone_number in FAKE_PHONE_NUMBERS:
        formatted_phone_number = None

    candidate_member = models.Member(
        name=row.name,
        primary_email_address=other_emails[0] if len(other_emails) > 0 else None,
        stripe_email_address=stripe_email,
        additional_email_addresses=other_emails[1:],
        phone_number=formatted_phone_number,
        slack_handle=None,
        notes=notes if notes else None,
    )

    existing_member_filter_criteria = []
    if len(other_emails) > 0:
        existing_member_filter_criteria.extend(
            Q(primary_email_address=email)
            | Q(stripe_email_address=email)
            | Q(additional_email_addresses__contains=[email])
            for email in other_emails + ([stripe_email] if stripe_email else [])
        )

    if formatted_phone_number:
        existing_member_filter_criteria.append(Q(phone_number=formatted_phone_number))

    existing_members = []
    if existing_member_filter_criteria:
        existing_members = list(
            Member.objects.filter(
                reduce(
                    operator.or_,
                    existing_member_filter_criteria,
                )
            ).order_by("id")
        )

    # This save call is placed strategically below the query above so that we don't get
    # candidate_member in the existing_members result set. We must save before the call to
    # merge_member_objects() since that requires doing m2m lookups for install object combination
    candidate_member.save()

    if existing_members:
        members_to_consolidate = existing_members + [candidate_member]
        min_id = min(m.id for m in members_to_consolidate)
        logging.debug(
            f"Duplicate entries detected at install # {row.id}. "
            f"Consolidating the following members: "
            f"{[(m.name, m.primary_email_address, m.phone_number) for m in members_to_consolidate]}"
        )
        merged_member = merge_member_objects(members_to_consolidate)

        # Now that we have consolidated down, clear out the objects we
        # consolidated to avoid duplication, and convert our new object to use the
        # min id of those objects (since a future merge may happen and if so we want to
        # ensure that this object is used as the source of truth)
        for member in members_to_consolidate:
            member.delete()

        Member.objects.filter(id=merged_member.id).update(id=min_id)
        return Member.objects.get(id=min_id), False

    return candidate_member, True
