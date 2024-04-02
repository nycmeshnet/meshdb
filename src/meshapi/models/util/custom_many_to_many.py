"""
!!!!

This file 100% copied from
https://forum.djangoproject.com/t/add-ability-to-define-custom-column-names-in-the-table-created-by-the-manytomanyfield/25427/6
except for two added lines (marked with "Andrew added me from the Django Forum post!")

We have exactly the same needs as the gentleman in this post. We want to rename the columns on the mapping table,
but don't want to make an additional through model and have to compromise on the helper functions, etc.

!!!!
"""

from functools import partial

from django.core.exceptions import ImproperlyConfigured
from django.db.models import ManyToManyField
from django.db.models.deletion import CASCADE
from django.db.models.fields.related import (
    RECURSIVE_RELATIONSHIP_CONSTANT,
    RelatedField,
    lazy_related_operation,
    resolve_relation,
)
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.db.models.utils import make_model_tuple
from django.utils.translation import gettext_lazy as _


def create_custom_column_name_many_to_many_intermediary_model(field, klass):
    from django.db import models

    def set_managed(model, related, through):
        through._meta.managed = model._meta.managed or related._meta.managed

    to_model = resolve_relation(klass, field.remote_field.model)
    name = "%s_%s" % (klass._meta.object_name, field.name)
    lazy_related_operation(set_managed, klass, to_model, name)

    # CHANGED FROM ORIGINAL: The following two lines are changed from the original django create_many_to_many_intermediary_model function
    to = getattr(field, "_to_column_name") or make_model_tuple(to_model)[1]
    from_ = getattr(field, "_from_column_name") or klass._meta.model_name
    if to == from_:
        to = "to_%s" % to
        from_ = "from_%s" % from_

    meta = type(
        "Meta",
        (),
        {
            "db_table": field._get_m2m_db_table(klass._meta),
            "auto_created": klass,
            "app_label": klass._meta.app_label,
            "db_tablespace": klass._meta.db_tablespace,
            "unique_together": (from_, to),
            "verbose_name": _("%(from)s-%(to)s relationship") % {"from": from_, "to": to},
            "verbose_name_plural": _("%(from)s-%(to)s relationships") % {"from": from_, "to": to},
            "apps": field.model._meta.apps,
        },
    )
    # Construct and return the new class.
    return type(
        name,
        (models.Model,),
        {
            "Meta": meta,
            "__module__": klass.__module__,
            from_: models.ForeignKey(
                klass,
                related_name="%s+" % name,
                db_column=from_,  # Andrew added me from the Django Forum post!
                db_tablespace=field.db_tablespace,
                db_constraint=field.remote_field.db_constraint,
                on_delete=CASCADE,
            ),
            to: models.ForeignKey(
                to_model,
                related_name="%s+" % name,
                db_column=to,  # Andrew added me from the Django Forum post!
                db_tablespace=field.db_tablespace,
                db_constraint=field.remote_field.db_constraint,
                on_delete=CASCADE,
            ),
        },
    )


class CustomColumnNameManyToManyField(ManyToManyField):
    # CHANGED FROM ORIGINAL: The following init method was added from original ManyToManyField() class
    def __init__(self, *args, db_from_column_name=None, db_to_column_name=None, **kwargs):
        if db_from_column_name is None or db_to_column_name is None:
            raise ImproperlyConfigured(
                "CustomColumnNameManyToManyField requires that you specify either db_from_column_name, db_to_column_name, or both."
            )
        self._from_column_name = db_from_column_name
        self._to_column_name = db_to_column_name
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if self.remote_field.symmetrical and (
            self.remote_field.model == RECURSIVE_RELATIONSHIP_CONSTANT
            or self.remote_field.model == cls._meta.object_name
        ):
            self.remote_field.related_name = "%s_rel_+" % name
        elif self.remote_field.is_hidden():
            # If the backwards relation is disabled, replace the original
            # related_name with one generated from the m2m field name. Django
            # still uses backwards relations internally and we need to avoid
            # clashes between multiple m2m fields with related_name == '+'.
            self.remote_field.related_name = "_%s_%s_%s_+" % (
                cls._meta.app_label,
                cls.__name__.lower(),
                name,
            )

        # CHANGED FROM ORIGINAL: The following line was changed from the original django ManyToManyField class
        RelatedField.contribute_to_class(self, cls, name, **kwargs)

        # The intermediate m2m model is not auto created if:
        #  1) There is a manually specified intermediate, or
        #  2) The class owning the m2m field is abstract.
        #  3) The class owning the m2m field has been swapped out.
        if not cls._meta.abstract:
            if self.remote_field.through:

                def resolve_through_model(_, model, field):
                    field.remote_field.through = model

                lazy_related_operation(resolve_through_model, cls, self.remote_field.through, field=self)
            elif not cls._meta.swapped:
                self.remote_field.through = (
                    # CHANGED FROM ORIGINAL: The following line was changed from the original django ManyToManyField class
                    create_custom_column_name_many_to_many_intermediary_model(self, cls)
                )

        # Add the descriptor for the m2m relation.
        setattr(cls, self.name, ManyToManyDescriptor(self.remote_field, reverse=False))

        # Set up the accessor for the m2m table name for the relation.
        self.m2m_db_table = partial(self._get_m2m_db_table, cls._meta)

    def deconstruct(self):
        # CHANGED FROM ORIGINAL: This method was added from the original django ManyToManyField class
        name, path, args, kwargs = super().deconstruct()
        if self._from_column_name is not None:
            kwargs["db_from_column_name"] = self._from_column_name
        if self._to_column_name is not None:
            kwargs["db_to_column_name"] = self._to_column_name
        return name, path, args, kwargs
