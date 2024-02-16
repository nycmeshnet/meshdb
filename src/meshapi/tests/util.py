from threading import Thread

from django.db import connection


class TestThread(Thread):
    def run(self):
        super().run()

        connection.close()
