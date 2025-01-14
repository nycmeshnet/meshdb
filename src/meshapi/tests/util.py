from threading import Thread

from bs4 import BeautifulSoup
from django.db import connection


class TestThread(Thread):
    def run(self):
        try:
            super().run()
        finally:
            connection.close()


def get_admin_results_count(html_string: str):
    soup = BeautifulSoup(html_string, "html.parser")
    result_list = soup.find(id="result_list")
    if not result_list:
        return 0

    return sum(1 for tr in result_list.find("tbody").find_all("tr") if tr.find_all("td"))
