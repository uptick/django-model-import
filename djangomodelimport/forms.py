from collections import defaultdict
from functools import partial

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS

from .fields import FlatRelatedField, SourceFieldSwitcher
from .magic import (
    CachedChoiceFieldFormMixin,
    FlatRelatedFieldFormMixin,
    JSONFieldFormMixin,
    SourceFieldSwitcherMixin,
)
from .utils import HasSource, ImportHeader
from .widgets import CompositeLookupWidget


class ImporterModelForm(
    SourceFieldSwitcherMixin,
    JSONFieldFormMixin,
    FlatRelatedFieldFormMixin,
    CachedChoiceFieldFormMixin,
    forms.ModelForm,
):
    """Extends the ModelForm to prime our caches and tweaks the validation
    routines to ensure we are not doing too many queries with our cached fields.
    """

    def __init__(self, data, caches, author=None, *args, **kwargs):
        self.caches = caches
        self.author = author
        self._warnings = defaultdict(list)
        super().__init__(data, *args, **kwargs)

    def add_warning(self, field: str, warning: str):
        # Mimic django form behaviour for errors
        if not field:
            field = NON_FIELD_ERRORS

        self._warnings[field].append(warning)

    @property
    def warnings(self):
        return dict(self._warnings)

    # This improves preview performance but eliminates validation on uniqueness constraints
    # def validate_unique(self):
    #     pass

    @classmethod
    def get_available_headers(cls) -> list[ImportHeader]:
        """Generate a list of available fields for the ImporterClass"""
        # 1) Evaluate Field type:
        # - SourceFieldSwitcher: these are a collection of different ways to find a related object.
        # - FlatRelatedField: these are a collection of other columns that build a relation on the fly.

        # 2) For each field, check its widget to see what headers it reads from
        # - Anything using NamedSourceWidget or has a "source" attr:
        #     these lookup columns might not match the form field.
        # - Anything using CompositeLookupWidget:
        #     these lookup columns might not always mention the form field target.
        # - Fields defined as attributes on the importer,
        #     but not listed as form fields (eg because they're used for postprocessing).

        # Gather help_texts and verbose_names from the model and importer class
        help_texts = getattr(cls.Meta, "help_texts", {})
        model_fields = {
            field.name: {
                "verbose_name": field.verbose_name,
                "help_text": field.help_text,
            }
            for field in cls.Meta.model._meta.fields
        }

        for key, value in model_fields.items():
            if value["help_text"] and key not in help_texts:
                help_texts[key] = value["help_text"]

        def _get_headers(name, widget, field_instance) -> list[ImportHeader]:
            """Evaluate the viable headers added by a field widget"""
            found_headers = []
            widget_required = True if widget and widget.is_required else False

            match widget:
                case CompositeLookupWidget(source=sub_fields):
                    # Collection of options for how a field is defined
                    for new_sub_headers in map(
                        partial(
                            _get_headers,
                            widget=None,
                            field_instance=field_instance,
                        ),
                        sub_fields,
                    ):
                        found_headers.extend(new_sub_headers)
                case HasSource(source=source):
                    # Renames the header for a field
                    # for example the "NamedSourceWidget"
                    found_headers.append(
                        ImportHeader(
                            field=field_instance,
                            field_name=field_name,
                            name=source,
                            help_text=help_texts.get(source, ""),
                            required=field.required or widget_required,
                        )
                    )
                case _:
                    # Anything else
                    found_headers.append(
                        ImportHeader(
                            field=field_instance,
                            field_name=field_name,
                            name=name,
                            help_text=help_texts.get(name, ""),
                            display=model_fields.get(name, {}).get("verbose_name", ""),
                            required=field.required or widget_required,
                        )
                    )

            return found_headers

        import_headers: list[ImportHeader] = []

        for field_name, field in cls.base_fields.items():
            match field:
                case SourceFieldSwitcher(fields=switch_fields):
                    # Containers a collections of ways to assign this field
                    temp_fields = []
                    for switch_field in switch_fields:
                        temp_fields.append(
                            _get_headers(field_name, switch_field.widget, switch_field)
                        )

                    new_field = temp_fields[0]
                    new_field[0].alternatives = temp_fields[1:]
                    import_headers.extend(new_field)
                case FlatRelatedField(fields=related_fields):
                    # Defines a way to create related objects from a set of headers
                    for new_fields in map(
                        partial(
                            _get_headers, widget=field.widget, field_instance=field
                        ),
                        related_fields.keys(),
                    ):
                        import_headers.extend(new_fields)
                case _:
                    fields = _get_headers(field_name, field.widget, field)
                    import_headers.extend(fields)

        return import_headers
