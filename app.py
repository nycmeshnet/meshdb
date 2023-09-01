from meshdb import app
from meshdb.db.setup import setup_db

print("Configuring DB...")
setup_db()

application = app
