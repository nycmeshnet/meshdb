import datetime
from typing import Optional

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


def javascript_time_to_internal_dt(datetime_int_val: Optional[int]) -> Optional[datetime.datetime]:
    if datetime_int_val is None:
        return None

    return datetime.datetime.fromtimestamp(datetime_int_val / 1000, tz=datetime.timezone.utc)


def dt_to_javascript_time(datetime_val: Optional[datetime.datetime]) -> Optional[int]:
    if datetime_val is None:
        return None

    return int(datetime_val.timestamp() * 1000)


@extend_schema_field(OpenApiTypes.INT)
class JavascriptDatetimeField(serializers.Field):
    def to_internal_value(self, date_int_val: Optional[int]) -> Optional[datetime.datetime]:
        return javascript_time_to_internal_dt(date_int_val)

    def to_representation(self, datetime_val: Optional[datetime.datetime]) -> Optional[int]:
        return dt_to_javascript_time(datetime_val)


@extend_schema_field(OpenApiTypes.INT)
class JavascriptDateField(serializers.Field):
    def to_internal_value(self, date_int_val: Optional[int]) -> Optional[datetime.date]:
        internal_dt = javascript_time_to_internal_dt(date_int_val)
        if not internal_dt:
            return None

        return internal_dt.date()

    def to_representation(self, date_val: Optional[datetime.date]) -> Optional[int]:
        if date_val is None:
            return None

        return dt_to_javascript_time(
            datetime.datetime.combine(
                date_val,
                datetime.datetime.min.time(),
            ).astimezone(datetime.timezone.utc)
        )
