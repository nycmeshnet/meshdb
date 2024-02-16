from typing import Optional

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer, raise_errors_on_nested_writes

from meshapi.models import Building, Install, Link, Member, Sector
from meshapi.permissions import check_has_model_view_permission


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class RecursiveSerializer(serializers.ModelSerializer):
    """
    A serializer which follows foreign-key relationships when serializing, taking care to avoid
    leaking data by checking user permissions as we recursively iterate through the objects. To
    prevent infinite recursive loops, use the exclude_fields parameter to specify the field name
    on this Serializer's model class which describes the "reverse" relationship back to the field
    that this serializer is being called to fill. Don't specify it for "root" serialization requests

    For de-serialization, we are able to accept either a data object which is a simple
    primary key pointing to this class in the DB, or a complex object which will be created/updated
    according the normal logic of the ModelSerializer class. However, we cannot accommodate nested
    object creation or updating at this time. Make separate POST or PUT requests to accomplish this
    """

    default_error_messages = {
        "required": _("This field is required."),
        "does_not_exist": _('Invalid pk "{pk_value}" - object does not exist.'),
        "incorrect_type": _("Incorrect type. Expected pk value, received {data_type}."),
        "nesting_detected": _(
            "Nested detected. Nesting is not permitted for write calls. Ensure all top-level fields are scalars"
        ),
    }

    def __init__(self, instance=None, data=empty, exclude_fields=None, **kwargs):
        super().__init__(instance, data, **kwargs)
        if exclude_fields is None:
            exclude_fields = []

        self.excluded_fields = exclude_fields

    def _field_is_excluded(self, field_name: str, user: Optional[User] = None, depth_limit: int = -1):
        # Remove explicitly excluded fields, this is primarily to prevent infinite recursive loops,
        # though this logic could probably be generalized into an ExcludedFieldSerializer class
        # if needed for other applications in the future
        if field_name in self.excluded_fields:
            return True

        # Do permissions-based checks and mutate objects that the user does not have permission
        # to access, so that they are reduced to only a pointer to a primary key
        # e.g. if the user doesn't have access to the member model, when we serialize it for the
        # Install model, it should look very empty:
        #    "member": { "id": 1 }
        # so that we do not leak data they do not have access to
        if not check_has_model_view_permission(user, self.Meta.model) or (
            depth_limit != -1 and self._current_recursive_depth > depth_limit
        ):
            if field_name != self.Meta.model._meta.pk.name:
                return True

        return False

    @property
    def _current_recursive_depth(self):
        if not self.parent:
            return 0
        else:
            if isinstance(self.parent, RecursiveSerializer):
                return self.parent._current_recursive_depth + 1
            elif isinstance(self.parent, ListSerializer):
                # "Skip over" the automatically added ListSerializers,
                # so we don't double count them or hit an error because they don't
                # implement RecursiveSerializer
                return self.parent.parent._current_recursive_depth + 1
            else:
                raise RuntimeError(
                    f"RecursiveSerializer cannot be used as a field on Serializers that"
                    f"do not themselves inherit from RecursiveSerializer. Our parent {self.parent} "
                    f"appears to be of type {self.parent.__class__.__name__}"
                )

    def get_fields(self):
        user = None
        depth_limit = -1
        request = self.context.get("request", None)
        if request:
            user = request.user
            depth_limit = int(request.query_params.get("max_recursion_depth", -1))

        output_fields = {}
        for field_key, serializer in super().get_fields().items():
            output_fields[field_key] = serializer

        return {
            field_key: serializer
            for field_key, serializer in super().get_fields().items()
            if not self._field_is_excluded(field_key, user, depth_limit)
        }

    def get_value(self, dictionary):
        # Note that this might break Django HTML forms in some cases. However, we're not using those
        # and we need to do this override because there appears to be a bug in how their detection
        # logic for those forms works, and the HTML code path is running errantly
        # See Serializer.get_value() for more info
        return dictionary.get(self.field_name, empty)

    def create(self, validated_data):
        try:
            raise_errors_on_nested_writes("create", self, validated_data)
        except AssertionError:
            self.fail("nesting_detected")

        return super().create(validated_data)

    def update(self, instance, validated_data):
        try:
            raise_errors_on_nested_writes("update", self, validated_data)
        except AssertionError:
            self.fail("nesting_detected")

        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        # If this seems like a whole object, attempt to deserialize it using our parent's method
        if isinstance(data, dict):
            return super().to_internal_value(data)

        # However if this is not a whole object, treat it as an PK and try to find it in our db
        try:
            if isinstance(data, bool):
                raise TypeError
            return self.Meta.model.objects.all().get(pk=data)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", pk_value=data)
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(data).__name__)


class BuildingSerializer(RecursiveSerializer):
    class Meta:
        model = Building
        fields = "__all__"

    # installs has been added below, scroll down to InstallSerializer to see it


class MemberSerializer(RecursiveSerializer):
    class Meta:
        model = Member
        fields = "__all__"

    all_email_addresses = serializers.ReadOnlyField()

    # installs has been added below, scroll down to InstallSerializer to see it


class InstallSerializer(RecursiveSerializer):
    class Meta:
        model = Install
        fields = "__all__"

    member = MemberSerializer(exclude_fields=["installs"])
    building = BuildingSerializer(exclude_fields=["installs"])


class LinkSerializer(RecursiveSerializer):
    class Meta:
        model = Link
        fields = "__all__"

    from_building = BuildingSerializer(exclude_fields=["links_from", "links_to"])
    to_building = BuildingSerializer(exclude_fields=["links_from", "links_to"])


class SectorSerializer(RecursiveSerializer):
    class Meta:
        model = Sector
        fields = "__all__"

    building = BuildingSerializer(exclude_fields=["sectors"])


# This is a bit hacky, but gets around the fact that we can't call InstallSerializer() until after
# MemberSerializer has already been declared
MemberSerializer._declared_fields["installs"] = InstallSerializer(exclude_fields=["member"], many=True, read_only=True)
BuildingSerializer._declared_fields["installs"] = InstallSerializer(
    exclude_fields=["building"], many=True, read_only=True
)
BuildingSerializer._declared_fields["links_from"] = LinkSerializer(
    exclude_fields=["building"],
    many=True,
    read_only=True,
)
BuildingSerializer._declared_fields["links_to"] = LinkSerializer(
    exclude_fields=["building"],
    many=True,
    read_only=True,
)
BuildingSerializer._declared_fields["sectors"] = SectorSerializer(
    exclude_fields=["building"],
    many=True,
    read_only=True,
)
