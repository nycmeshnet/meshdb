import csv
import logging
import os
import sys
import time
from io import StringIO

import bs4
import django
import requests

from meshdb.utils.spreadsheet_import import logger

logger.configure()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")
django.setup()

from meshapi.models import Install


def download_export(session, export_id):
    download_response = session.get("https://support.nycmesh.net/scp/export.php?id=" + export_id)

    if download_response.status_code == 416:
        return None

    if download_response.status_code != 200:
        download_response.raise_for_status()

    logging.info("Downloading OSTicket Export....")
    return download_response.text


def attempt_to_load_osticket_data(queue_number):
    username = os.environ.get("OSTICKET_USER")
    password = os.environ.get("OSTICKET_PASSWORD")

    if not username or not password:
        raise EnvironmentError("OSTICKET_USER and OSTICKET_PASSWORD env vars must be set")

    logging.info(f"Authenticating to OSTicket (queue {queue_number})....")

    session = requests.Session()
    response_for_csrf = session.get("https://support.nycmesh.net")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    soup = bs4.BeautifulSoup(response_for_csrf.text, "html.parser")
    csrf_token = soup.find("meta", attrs={"name": "csrf_token"}).get("content")

    assert csrf_token

    login_response = session.post(
        "https://support.nycmesh.net/scp/login.php",
        data={
            "__CSRFToken__": csrf_token,
            "do": "scplogin",
            "userid": "andrew.dickinson.0216@gmail.com",
            "passwd": "kFydO9WJDLonP3wG",
            "ajax": "1",
        },
        headers=headers,
    )
    assert login_response.json() == {"status": 302, "redirect": "index.php"}

    logging.info(f"Requestng OSTicket Export (queue {queue_number})....")
    export_response = session.post(
        f"https://support.nycmesh.net/scp/ajax.php/tickets/export/{queue_number}",
        headers=headers,
        data=[
            ("fields[]", "number"),
            ("fields[]", "cdata__subject"),
            ("fields[]", "topic_id"),
            ("fields[]", "cdata__node"),
            ("fields[]", "cdata__rooftop"),
            ("filename", "Closed Tickets - ABC.csv"),
            ("csv-delimiter", ","),
            ("undefined", "Export"),
            ("__CSRFToken__", csrf_token),
        ],
    )
    eid = export_response.json()["eid"]

    logging.info(f"Waiting for OSTicket Export to complete (queue {queue_number})....")
    csv_contents = download_export(session, eid)
    attempts = 1
    while csv_contents is None:
        csv_contents = download_export(session, eid)
        attempts += 1
        time.sleep(5)

        if attempts > 20:
            raise TimeoutError("Too many attempts to download export data")

    f = StringIO(csv_contents)
    reader = csv.DictReader(f)
    return list(reader)


def parse_node_text_to_install_number(node_text):
    if not node_text:
        return None

    try:
        return int(node_text)
    except ValueError:
        modified_text = node_text.strip().replace("#", "").split(" ")[0]
        try:
            return int(modified_text)
        except ValueError:
            logging.error(f"Bad node: {node_text}")
            return None


def import_ticket_numbers_from_osticket():
    attempts = 0
    while True:
        try:
            attempts += 1
            closed_tickets = attempt_to_load_osticket_data("8")
            break
        except Exception as e:
            if attempts > 3:
                raise e

    while True:
        try:
            attempts += 1
            open_tickets = attempt_to_load_osticket_data("1")
            break
        except Exception as e:
            if attempts > 3:
                raise e

    logging.info("Loading ticket numbers into install objects...")
    for ticket in open_tickets + closed_tickets:
        if ticket["node"]:
            install_number = parse_node_text_to_install_number(ticket["node"])
            if install_number:
                ticket_number = ticket["Ticket Number"]
                install: Install = Install.objects.filter(install_number=install_number).first()
                if install:
                    install.ticket_number = ticket_number
                    install.save()


if __name__ == "__main__":
    import_ticket_numbers_from_osticket()
