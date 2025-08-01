
from typing import Optional
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from validate_email.exceptions import EmailValidationError
from meshapi.validation import normalize_phone_number, validate_email_address, validate_phone_number
from meshapi.views.forms import JoinFormRequest


def process_join_form_v2(r: JoinFormRequest, request: Optional[Request] = None) -> Response:
    # Ensure the member has accepted the NCL
    if not r.ncl:
        return Response(
            {"detail": "You must agree to the Network Commons License!"}, status=status.HTTP_400_BAD_REQUEST
        )

    join_form_full_name = f"{r.first_name} {r.last_name}"

    # Validate Email Address
    if not r.email_address:
        return Response({"detail": "Must provide an email"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if r.email_address and not validate_email_address(r.email_address):
            return Response({"detail": f"{r.email_address} is not a valid email"}, status=status.HTTP_400_BAD_REQUEST)
    except EmailValidationError:
        # DNSTimeoutError, SMTPCommunicationError, and TLSNegotiationError are all subclasses of EmailValidationError.
        # Any other EmailValidationError will be caught inside validate_email_address() and trigger a return false,
        # so we know that if validate_email_address() throws, EmailValidationError, it must be one of these
        # and therefore our fault
        return Response(
            {"detail": "Could not validate email address due to an internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Validate Phone Number
    # Expects country code!!!!
    if r.phone_number and not validate_phone_number(r.phone_number):
        return Response({"detail": f"{r.phone_number} is not a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

    formatted_phone_number = normalize_phone_number(r.phone_number) if r.phone_number else None

    # Validate Address




