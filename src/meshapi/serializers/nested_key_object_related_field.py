from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import PrimaryKeyRelatedField


class NestedKeyObjectRelatedField(serializers.RelatedField):
    """
    A RelatedField class which references the related object via a concise set of identifying keys.

    For example, for a foreign key to node this will look like:
    ```json
    {"id": "uuid-here", "network_number": nn_here}
    ```
    By default, only the `id` key is present, but additional keys can be provided with the `additional_keys` kwarg.

    For writes, we allow setting any non-empty subset of the key values, so long as all provided key, value
    lookups reference the same object. Giving invalid or inconsistent key values will result in a ValidationError
    """

    default_error_messages = PrimaryKeyRelatedField.default_error_messages

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.additional_keys: Tuple[str, ...] = ()
        if "additional_keys" in kwargs:
            self.additional_keys = kwargs.pop("additional_keys")

        super().__init__(*args, **kwargs)

    def _get_key_fields(self) -> Tuple[str, ...]:
        return ("id",) + self.additional_keys

    def to_representation(self, value: Model) -> dict[str, Any]:
        return {key: getattr(value, key) for key in self._get_key_fields()}

    def to_internal_value(self, data: dict) -> Model:
        queryset = self.get_queryset()

        if not isinstance(data, dict):
            raise ValidationError(
                "Serialized foreign keys values must be nested objects which specify one or more key names"
            )

        if not len(data.items()):
            raise ValidationError("You must provide at least one object key")

        referenced_objects = []
        for key, value in data.items():
            if key not in self._get_key_fields():
                raise ValidationError(
                    f"Invalid key for model reference: '{key}'. Valid values are {self._get_key_fields()}"
                )

            try:
                if isinstance(value, bool) or value is None:
                    raise TypeError
                referenced_objects.append(queryset.get(**{key: value}))
            except ObjectDoesNotExist:
                self.fail("does_not_exist", pk_value=value)
            except (TypeError, ValueError):
                self.fail("incorrect_type", data_type=type(value).__name__)

        if not all(obj == referenced_objects[0] for obj in referenced_objects):
            raise serializers.ValidationError(f"Provided keys do not reference the same object: {data}")

        return referenced_objects[0]


class NestedKeyRelatedMixIn(ModelSerializer):
    """
    A  ModelSerializer MixIn which sets `NestedKeyObjectRelatedField` as the default field class
    to use for the foreign key fields
    """

    serializer_related_field = NestedKeyObjectRelatedField
