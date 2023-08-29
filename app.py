from meshdb import app
from meshdb.db.setup import setup_db

if __name__ == "__main__":
    print("Configuring DB...")
    setup_db()

    app.run(host=app.config["IP"], port=app.config["PORT"])

application = app
