"""
WSGI config for meshdb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

# Initialize dogstatsd
from datadog import initialize
from django.core.wsgi import get_wsgi_application

initialize(statsd_host="datadog-agent.datadog.svc.cluster.local", statsd_port=8125)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meshdb.settings")

application = get_wsgi_application()
