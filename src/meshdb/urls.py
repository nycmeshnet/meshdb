"""
URL configuration for meshdb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

from meshapi.docs import SpectacularSwaggerInjectVarsView
from meshdb.settings import PROFILING_ENABLED

urlpatterns = [
    path("", include("meshweb.urls")),
    path("auth/", include("rest_framework.urls")),
    path("admin/", admin.site.urls),
    path("api/v1/", include("meshapi.urls")),
    path("api-docs/openapi3.json", SpectacularAPIView.as_view(), name="api-docs-schema"),
    path(
        "api-docs/swagger/",
        SpectacularSwaggerInjectVarsView.as_view(
            url_name="api-docs-schema"  # , template_name="drf_spectacular/swagger_ui.html"
        ),
        name="api-docs-swagger",
    ),
    path("api-docs/redoc/", SpectacularRedocView.as_view(url_name="api-docs-schema"), name="api-docs-redoc"),
]

if PROFILING_ENABLED:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
