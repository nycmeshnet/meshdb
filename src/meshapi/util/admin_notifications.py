from typing import Sequence, Type

from django.db.models import Model
from rest_framework.serializers import Serializer


def notify_administrators_of_data_issue(
    model_instances: Sequence[Model],
    serializer_class: Type[Serializer],
    message: str,
) -> None:
    # TODO: Implement me & write a unit test that ensures we make the right slack API call
    raise NotImplementedError()
