import logging
import os
import time

import requests
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.dispatch import receiver

from meshapi.models import Install

OSTICKET_API_TOKEN = os.environ.get("OSTICKET_API_TOKEN")
OSTICKET_NEW_TICKET_ENDPOINT = os.environ.get("OSTICKET_NEW_TICKET_ENDPOINT")


@receiver(post_save, sender=Install, dispatch_uid="create_os_ticket_for_install")
def create_os_ticket_for_install(sender: ModelBase, instance: Install, created: bool, **kwargs: dict) -> None:
    if not created:
        return

    install: Install = instance
    if not OSTICKET_API_TOKEN or not OSTICKET_NEW_TICKET_ENDPOINT:
        logging.error(
            f"Unable to create ticket for install {str(install)}, did you set the OSTICKET_API_TOKEN "
            f"and OSTICKET_NEW_TICKET_ENDPOINT env vars?"
        )
        return

    name = install.member.name
    # email = install.member.primary_email_address
    email = "andrew@nycmesh.net"  # TODO: for testing. Disable to send emails for real
    phone = install.member.phone_number
    location = install.one_line_complete_address
    rooftop_access = install.roof_access
    ncl = True
    timestamp = install.request_date
    id = install.install_number

    if not email:
        logging.warning(
            f"Not creating OSTicket for install {str(install)}. Member {str(install.member)} "
            f"does not have a primary email address"
        )
        return

    if rooftop_access:
        rooftop = "Rooftop install"
        emailTitle = f"NYC Mesh {id} Rooftop Install"
    else:
        rooftop = "Standard install"
        emailTitle = f"NYC Mesh {id} Install"

    message = f"date: {timestamp}\r\n"
    message += f"node: {id}\r\n"
    message += f"name: {name}\r\n"
    message += f"email: {email}\r\n"
    message += f"phone: {phone}\r\n"
    message += f"location: {location}\r\n"
    message += f"rooftop: {rooftop}\r\n"
    message += f"agree to ncl: {ncl}"

    data = {
        "node": id,
        "userNode": id,
        "email": email,
        "name": name,
        "subject": emailTitle,
        "message": message,
        "phone": phone,
        "location": location,
        "rooftop": rooftop,
        "ncl": ncl,
        "ip": "*.*.*.*",
        "locale": "en",
    }

    attempts = 0
    while attempts < 4:
        attempts += 1
        response = requests.post(
            OSTICKET_NEW_TICKET_ENDPOINT,
            json=data,
            headers={"X-API-Key": OSTICKET_API_TOKEN},
        )

        if response.status_code == 201:
            break

        time.sleep(1)

    if response.status_code != 201:
        logging.error(
            f"Unable to create ticket for install {str(install)}. OSTicket returned "
            f"HTTP {response.status_code}: {response.text}"
        )
        return

    # If we got a good response, update the install object to reflect the ticket ID we just created
    install.ticket_number = response.text
    install.save()
