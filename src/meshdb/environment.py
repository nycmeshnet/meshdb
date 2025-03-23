import os

#from settings.py
MESHDB_ENVIRONMENT = os.environ.get("MESHDB_ENVIRONMENT", "")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "False") == "True"
PROFILING_ENABLED = DEBUG and not os.environ.get("DISABLE_PROFILING", "False") == "True"
LOS_URL = os.environ.get("LOS_URL", "https://los.devdb.nycmesh.net")
MAP_URL = os.environ.get("MAP_BASE_URL", "https://map.nycmesh.net")
FORMS_URL = os.environ.get("FORMS_URL", "https://forms.devdb.nycmesh.net")
EMAIL_HOST = os.environ.get("SMTP_HOST")
EMAIL_PORT = os.environ.get("SMTP_PORT")
EMAIL_HOST_USER = os.environ.get("SMTP_USER")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_USER_RO = os.environ.get("DB_USER_RO")
DB_PASSWORD_RO = os.environ.get("DB_PASSWORD_RO")

# from celery.py
CELERY_BROKER = os.environ.get("CELERY_BROKER", "redis://localhost:6379/0")


#from pelias.py
PELIAS_ADDRESS_PARSER_URL = os.environ.get("PELIAS_ADDRESS_PARSER_URL", "http://localhost:6800/parser/parse")

#from validation.py
RECAPTCHA_SECRET_KEY_V2 = os.environ.get("RECAPTCHA_SERVER_SECRET_KEY_V2")
RECAPTCHA_SECRET_KEY_V3 = os.environ.get("RECAPTCHA_SERVER_SECRET_KEY_V3")
RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD = float(os.environ.get("RECAPTCHA_INVISIBLE_TOKEN_SCORE_THRESHOLD", 0.5))

#from fetch_uisp.py
UISP_URL = os.environ.get("UISP_URL")
UISP_USER = os.environ.get("UISP_USER")
UISP_PASS = os.environ.get("UISP_PASS")

#from osticket_creation.py
OSTICKET_API_TOKEN = os.environ.get("OSTICKET_API_TOKEN")
OSTICKET_NEW_TICKET_ENDPOINT = os.environ.get("OSTICKET_NEW_TICKET_ENDPOINT")
OSTICKET_URL = os.environ.get("OSTICKET_URL", "https://support.nycmesh.net"
                              )
#from join_requests_slack_channel.py
SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL = os.environ.get("SLACK_JOIN_REQUESTS_CHANNEL_WEBHOOK_URL")

#from join_records.py
JOIN_RECORD_ENDPOINT = os.environ.get("S3_ENDPOINT", None)
JOIN_RECORD_BUCKET_NAME = os.environ.get("JOIN_RECORD_BUCKET_NAME")
JOIN_RECORD_PREFIX = os.environ.get("JOIN_RECORD_PREFIX")

#from admin_notifications.py
SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL = os.environ.get("SLACK_ADMIN_NOTIFICATIONS_WEBHOOK_URL")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL")

#from panoramas.py
token = os.environ.get("PANO_GITHUB_TOKEN")

#from test_update_panos_github.py
PANO_REPO_OWNER = os.environ.get("PANO_REPO_OWNER") or "nycmeshnet"
PANO_REPO = os.environ.get("PANO_REPO") or "node-db"
PANO_BRANCH=os.environ.get("PANO_BRANCH") or "master"
PANO_DIR = os.environ.get("PANO_DIR") or "data/panoramas"
PANO_HOST= os.environ.get("PANO_HOST") or "http://example.com"
PANO_GITHUB_TOKEN = os.environ.get("PANO_GITHUB_TOKEN") or "4"

#from test_query_form.py
QUERY_PSK = os.environ.get("QUERY_PSK")


NN_ASSIGN_PSK = os.environ.get("NN_ASSIGN_PSK")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", " ")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", " ")




