"""
WSGI config for meshdb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Initialize dogstatsd
from datadog import initialize
options = {
    'statsd_host':'127.0.0.1',
    'statsd_port':8125
}
initialize(**options)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")

application = get_wsgi_application()
