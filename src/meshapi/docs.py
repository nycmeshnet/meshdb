import json
from textwrap import dedent
from typing import Any, Dict, List, Optional

from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from drf_spectacular.authentication import SessionScheme
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.views import SpectacularSwaggerView


class SpectacularSwaggerInjectVarsView(SpectacularSwaggerView):
    @extend_schema(exclude=True)
    def get(self, request: HttpRequest, *args: List[Any], **kwargs: Dict[str, Any]) -> HttpResponse:
        spectacular_settings.DESCRIPTION = (
            "Programmatic access to mesh core data, detailing our installs, members, etc. "
            '\n\nTo use an authorization token, use the "Authorize" button, and under "tokenAuth" enter '
            "`Token ` before the content of your token, like this: `Token xxxyyyyyzzz`"
            "\n\nIf you have username/password credentials (like those used on the admin UI) you can login "
            f'via the admin UI or [DRF login page]({reverse("rest_framework:login")}?next=/api-docs/swagger/)'
        )
        response = super().get(request, *args, **kwargs)
        session_id = request.session.session_key
        response.data[
            "settings"
        ] = f"""
            {json.dumps(spectacular_settings.SWAGGER_UI_SETTINGS, indent=2)[:-2]},
            deepLinking: true,
            onComplete: ui_onComplete,
            plugins: [LogoutViaDjango],
        }};
        const logoutURL = "{reverse("rest_framework:logout")}";
        """
        if session_id:
            response.data["settings"] += 'const sessionID = "{session_id}";'

        return response


# Borrowed from here
# https://github.com/tfranzel/drf-spectacular/issues/1099#issuecomment-1920345459
class SessionSchemeModified(SessionScheme):
    name = "Session ID"
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            **super().get_security_definition(auto_schema),
            "description": dedent(
                f"""
                **This will be configured automatically in the Swagger UI
                documentation if there is currently a user logged in via the Django Rest Framework
                [login page]({reverse("rest_framework:login")}?next=/api-docs/swagger/).**
            """
            ),
        }


nn_assignment_password_param = OpenApiParameter(
    "password",
    OpenApiTypes.PASSWORD,
    OpenApiParameter.QUERY,
    required=True,
    description="The password for the legacy NN assignment form",
)

query_form_password_param = OpenApiParameter(
    "password",
    OpenApiTypes.PASSWORD,
    OpenApiParameter.QUERY,
    required=True,
    description="The password for the legacy query form",
)


def map_query_filters_to_param_annotations(query_filters: Dict[str, Optional[str]]) -> List[OpenApiParameter]:
    param_annotations = []
    for param_name, filter_strategy in query_filters.items():
        filter_strategy_human_readable = {
            None: "strict equality",
            "iexact": "strict equality",
            "icontains": "substring matching",
        }
        param_annotations.append(
            OpenApiParameter(
                param_name,
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=f"Filter results by the `{param_name}` field using "
                f"{filter_strategy_human_readable[filter_strategy]}",
                required=False,
            )
        )

    return param_annotations
