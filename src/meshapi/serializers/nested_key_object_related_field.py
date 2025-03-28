import typing
from typing import Any, Dict, Tuple, cast, Optional
from uuid import UUID

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from drf_spectacular import drainage
from drf_spectacular.extensions import OpenApiSerializerFieldExtension, _SchemaType
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import append_meta, build_basic_type, build_object_type, follow_field_source
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import Direction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer


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

        self.additional_keys_display_permission: Optional[str] = None
        if "additional_keys_display_permission" in kwargs:
            if not self.additional_keys:
                raise ValidationError("additional_keys_display_permission requires additional_keys")

            self.additional_keys_display_permission = kwargs.pop("additional_keys_display_permission")

        super().__init__(*args, **kwargs)

    def _get_key_fields(self) -> Tuple[str, ...]:
        non_sensitive_keys = ("id",)

        user: Optional[User] = self.context["request"].user if self.context["request"] else None
        if not self.additional_keys_display_permission or (
            user and user.has_perm(self.additional_keys_display_permission)
        ):
            return non_sensitive_keys + self.additional_keys

        return non_sensitive_keys

    def to_representation(self, value: Model) -> dict[str, Any]:
        output = {}
        for key in self._get_key_fields():
            output[key] = getattr(value, key)

            # Convert UUID objects to str so that the resulting data
            # is trivially JSON serializable
            if isinstance(output[key], UUID):
                output[key] = str(output[key])

        return output

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


class NestedKeyObjectRelatedFieldDRFSpectacularFix(OpenApiSerializerFieldExtension):  # type: ignore
    """
    This class overrides the handling of swagger documentation generation for the NestedKeyObjectRelatedField,
    which is needed since DRF spectactular's default handling for RelatedField objects is not at all
    compatible with our nested key objects

    We ignore type checks because DRF spectacular is built on a mountain of dynamic type check sand nonsense
    and so trying to strongly type an extension is pretty much doomed
    """

    target_class = NestedKeyObjectRelatedField

    @typing.no_type_check
    def map_serializer_field(self, auto_schema: AutoSchema, direction: Direction) -> _SchemaType:
        meta = auto_schema._get_serializer_field_meta(self.target, direction)
        if getattr(self.target, "queryset", None) is not None:
            related_model: Model = self.target.queryset.model
        else:
            if isinstance(self.target.parent, serializers.ManyRelatedField):
                model = self.target.parent.parent.Meta.model
                source = self.target.parent.source.split(".")
            elif hasattr(self.target.parent, "Meta"):
                model = self.target.parent.Meta.model
                source = self.target.source.split(".")
            else:
                drainage.warn(
                    f"Could not derive type for under-specified {self.target.__class__.__name__} "
                    f'"{self.target.field_name}". The serializer has no associated model (Meta class) '
                    f"and this particular field has no type without a model association. Consider "
                    f"changing the field or adding a Meta class. defaulting to string."
                )
                return cast(_SchemaType, build_basic_type(OpenApiTypes.STR))

            related_model = follow_field_source(model, source).model

        schemas: Dict[str, _SchemaType] = {}
        for key in self.target._get_key_fields():
            model_field = getattr(related_model, key).field
            schemas[key] = auto_schema._map_model_field(model_field, direction)

            # primary keys are usually non-editable (readOnly=True) and map_model_field correctly
            # signals that attribute. however this does not apply in the context of relations.
            schemas[key].pop("readOnly", None)

        return append_meta(
            build_object_type(
                properties=schemas,
                description=f"A reference to a {related_model._meta.object_name} object, via one or "
                f"more of the following keys: {list(schemas.keys())}",
            ),
            meta,
        )
