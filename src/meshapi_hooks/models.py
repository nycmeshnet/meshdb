from django.db import models

# drf-hooks looks in this file for hook objects, but it feels weird to inline
# it here, so we import it instead
from .hooks import CeleryRecursiveSerializerHook
