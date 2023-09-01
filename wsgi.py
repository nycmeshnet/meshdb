from meshdb import create_app
from meshdb.db.setup import setup_db

print("Configuring DB...")
setup_db()

app = create_app()

app.run(host=app.config["IP"], port=app.config["PORT"])
