import csv
import json
import os
import re
import sys
from csv import DictReader
from typing import List

import requests
import stripe

stripe.api_key = os.environ["STRIPE_API_TOKEN"]
MESHDB_API_TOKEN = os.environ["MESHDB_API_TOKEN"]


def find_install_numbers_by_stripe_email(stripe_email: str) -> List[str]:
    member_response = requests.get(
        f"https://db.nycmesh.net/api/v1/members/lookup/?email_address={stripe_email}",
        headers={"Authorization": f"Token {MESHDB_API_TOKEN}"},
    )
    member_response.raise_for_status()

    member_data = member_response.json()

    stripe_email_explicit_installs = []
    active_installs = []
    other_installs = []
    for member in member_data["results"]:
        for install in member["installs"]:
            install_detail_response = requests.get(
                f"https://db.nycmesh.net/api/v1/installs/{install['id']}",
                headers={"Authorization": f"Token {MESHDB_API_TOKEN}"},
            )
            install_detail_response.raise_for_status()
            install_detail = install_detail_response.json()
            if member["stripe_email_address"] == stripe_email:
                stripe_email_explicit_installs.append(install_detail)
            elif install_detail["status"] == "Active":
                active_installs.append(install_detail)
            else:
                other_installs.append(install_detail)

    return [
        str(install["install_number"]) for install in stripe_email_explicit_installs + active_installs + other_installs
    ]


def get_subscription_ids_for_charge_id(charge_id: str) -> List[str]:
    try:
        # Retrieve the charge
        charge = stripe.Charge.retrieve(charge_id)

        # Extract the customer ID from the charge (if present)
        customer_id = charge.get("customer")
        if not customer_id:
            return []

        # Retrieve all subscriptions for the customer
        subscriptions = stripe.Subscription.list(customer=customer_id)

        return [sub.id for sub in subscriptions.auto_paging_iter()]
    except stripe.error.StripeError as e:
        print(f"Stripe API error: {e.user_message or str(e)}")
        return []
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return []


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <stripe-csv-file> <slack-export-file>")
        sys.exit(1)

    print("Parsing slack export...")
    slack_charge_mapping = {}
    slack_export_file = sys.argv[2]
    with open(slack_export_file, "r") as f:
        slack_data = json.load(f)
        for message in slack_data["messages"]:
            if message.get("slackdump_thread_replies") and message.get("attachments"):
                text_description = message["attachments"][0]["text"]
                if "https://manage.stripe.com/payments" in text_description and "charged" in text_description:
                    stripe_id_match = re.search(r"https://manage\.stripe\.com/payments/(ch_.*)\|", text_description)
                    if stripe_id_match:
                        stripe_charge_id = stripe_id_match.group(1)
                        # print(message["attachments"][0]["text"])
                        # print(stripe_id)
                        replies = [reply["text"] for reply in message["slackdump_thread_replies"] if reply.get("text")]
                        # print(replies)
                        replies_joined = "\n".join(replies)
                        if "thank you" in replies_joined.lower():
                            continue

                        install_number_pound_match = re.search(r"#(\d{3,5})", replies_joined)
                        if install_number_pound_match:
                            slack_charge_mapping[stripe_charge_id] = install_number_pound_match.group(1)
                            continue

                        install_number_match = re.search(
                            r"(?<!NY\s)(?<!NY,\s)(?<!Address:\s)(?<!Address:\s\s)\b(\d{4,5})\b", replies_joined
                        )
                        if install_number_match:
                            install_number = install_number_match.group(1)
                            if install_number not in [
                                "1932",
                                "1933",
                                "1934",
                                "1936",
                                "2019",
                                "2020",
                                "2021",
                                "2022",
                                "2023",
                                "2024",
                                "2025",
                                "10002",
                            ]:
                                slack_charge_mapping[stripe_charge_id] = install_number
                                continue

    print("Querying stripe to convert payment IDs to subscription IDs...")
    slack_subscription_mapping = {}
    for i, (stripe_charge_id, install_number) in enumerate(slack_charge_mapping.items()):
        if i % 100 == 0:
            print(f"{i} / {len(slack_charge_mapping)}")

        stripe_subscription_ids = get_subscription_ids_for_charge_id(stripe_charge_id)
        for stripe_subscription_id in stripe_subscription_ids:
            if stripe_subscription_id not in slack_subscription_mapping:
                slack_subscription_mapping[stripe_subscription_id] = []
            slack_subscription_mapping[stripe_subscription_id].append(install_number)

    print("Loading stripe CSV export...")
    stripe_csv_filename = sys.argv[1]
    stripe_csv_data = []
    with open(stripe_csv_filename, "r") as csv_file:
        reader = DictReader(csv_file)
        fieldnames = list(reader.fieldnames) + ["install_nums_email", "install_nums_slack"]

        for row in reader:
            stripe_csv_data.append(row)

    print("Querying MeshDB to do email-based lookups...")
    output_data = []
    for i, row in enumerate(stripe_csv_data):
        if i % 100 == 0:
            print(f"{i} / {len(stripe_csv_data)}")

        stripe_email = row["Customer Email"]
        if stripe_email:  # Some rows are blank
            install_numbers = find_install_numbers_by_stripe_email(stripe_email)
            row["install_nums_email"] = ",".join(install_numbers)
            row["install_nums_slack"] = ",".join(slack_subscription_mapping.get(row["id"]) or [])
            output_data.append(row)

    print("Writing output file...")
    with open("output.csv", "w") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_data:
            writer.writerow(row)


if __name__ == "__main__":
    main()
