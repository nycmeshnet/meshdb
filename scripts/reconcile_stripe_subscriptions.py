import csv
import os
import sys
from csv import DictReader
from typing import List, Optional

import requests

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


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <stripe-csv-file>")
        sys.exit(1)

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
                    row["install_nums"] = ",".join(install_numbers)
                    writer.writerow(row)


if __name__ == "__main__":
    main()
