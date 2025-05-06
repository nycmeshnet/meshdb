import csv
import json
import os
import re
import sys
from csv import DictReader

import requests
import stripe
from typing import List

stripe.api_key = os.environ["STRIPE_API_TOKEN"]
MESHDB_API_TOKEN = os.environ["MESHDB_API_TOKEN"]


def find_install_numbers_by_stripe_email(stripe_email: str) -> List[str]:
    member_response = requests.get(
        f"https://db.nycmesh.net/api/v1/members/lookup/?email_address={stripe_email}",
        headers={"Authorization": f"Token {MESHDB_API_TOKEN}"},
    )
    member_response.raise_for_status()

    member_data = member_response.json()

    install_numbers = []
    for member in member_data["results"]:
        for install in member["installs"]:
            install_detail_response = requests.get(
                f"https://db.nycmesh.net/api/v1/installs/{install['id']}",
                headers={"Authorization": f"Token {MESHDB_API_TOKEN}"},
            )
            install_detail_response.raise_for_status()
            install_detail = install_detail_response.json()

            if install_detail["status"] == "Active":
                install_numbers.append(str(install["install_number"]))

    return install_numbers


def get_subscription_ids_for_charge_id(charge_id: str) -> List[str]:
    try:
        # Retrieve the charge
        charge = stripe.Charge.retrieve(charge_id)

        # Extract the customer ID from the charge
        customer_id = charge.get("customer")
        if not customer_id:
            raise ValueError(f"Charge {charge_id} does not have a customer associated with it.")

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

    slack_subscription_mapping = {}
    for stripe_charge_id, install_number in slack_charge_mapping.items():
        stripe_subscription_ids = get_subscription_ids_for_charge_id(stripe_charge_id)
        for stripe_subscription_id in stripe_subscription_ids:
            if stripe_subscription_id not in slack_subscription_mapping:
                slack_subscription_mapping[stripe_subscription_id] = []
            slack_subscription_mapping[stripe_subscription_id].append(install_number)

    stripe_csv_filename = sys.argv[1]
    with open(stripe_csv_filename, "r") as csv_file:
        reader = DictReader(csv_file)

        with open("output.csv", "w") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=list(reader.fieldnames) + ["install_nums"])

            for row in reader:
                stripe_email = row["Customer Email"]
                if stripe_email:  # Some rows are blank
                    print(row["Customer Email"])
                    install_numbers = find_install_numbers_by_stripe_email(stripe_email)
                    row["install_nums_email"] = ",".join(install_numbers)
                    row["install_num_slack"] = ",".join(slack_subscription_mapping.get(row["id"]) or [])
                    writer.writerow(row)


if __name__ == "__main__":
    main()
