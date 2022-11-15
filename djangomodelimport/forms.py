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
from .utils import HasSource, ImportFieldMetadata
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

    def __init__(self, data, caches, author=None, *args, **kwargs) -> None:
        self.caches = caches
        self.author = author
        self._warnings = defaultdict(list)
        super().__init__(data, *args, **kwargs)

    def add_warning(self, field: str, warning: str) -> None:
        # Mimic django form behaviour for errors
        if not field:
            field = NON_FIELD_ERRORS

        self._warnings[field].append(warning)

    @property
    def warnings(self) -> dict[str, list[str]]:
        return dict(self._warnings)

    # This improves preview performance but eliminates validation on uniqueness constraints
    # def validate_unique(self):
    #     pass

    @classmethod
    def get_available_headers(cls) -> list[tuple[str, str]]:
        """Returns a list of headers available on the import form

        Returned as a tuple of (key, label)
        """
        fields = cls.get_field_metadata()

        header_set = {"id"}
        headers = [("id", "ID")]

        for field in fields.values():
            for sources in field.sources:
                for header, label in sources:
                    if header not in header_set:
                        header_set.add(header)
                        headers.append((header, label))

        return headers

    @classmethod
    def get_field_metadata(cls) -> dict[str, ImportFieldMetadata]:
        """Generate a dict of available fields for the ImporterClass"""
        # 1) Evaluate Field type:
        # - SourceFieldSwitcher: these are a collection of different ways to find a related object.
        # - FlatRelatedField: these are a collection of other columns that build a relation on the fly.

        # 2) For each field, check its widget to see what headers it can source from
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
                "label": field.verbose_name.title(),
                "help_text": field.help_text,
            }
            for field in cls.Meta.model._meta.fields
        }

        for key, value in model_fields.items():
            if value["help_text"] and key not in help_texts:
                help_texts[key] = value["help_text"]

        def _get_headers(name, widget) -> list[tuple[str, str]]:
            """Evaluate the viable headers added by a field widget"""
            found_headers = []

            match widget:
                case CompositeLookupWidget(source=sub_fields):
                    # Collection of options for how a field is defined
                    for new_sub_headers in map(
                        partial(
                            _get_headers,
                            widget=None,
                        ),
                        sub_fields,
                    ):
                        found_headers.extend(new_sub_headers)
                case HasSource(source=str(source)):
                    # Renames the header for a field
                    # for example the "NamedSourceWidget"
                    found_headers.extend(_get_headers(source, widget=None))
                case HasSource(source=sources):
                    # Renames the header for a field
                    # for example the "NamedSourceWidget"
                    for source in sources:
                        found_headers.extend(_get_headers(source, widget=None))
                case _:
                    # Anything else
                    found_headers.append(
                        (
                            name,
                            model_fields.get(name, {}).get(
                                "label", name.replace("_", " ").title()
                            ),
                        )
                    )

            return found_headers

        import_fields: dict[str, ImportFieldMetadata] = {}

        for field_name, field_instance in cls.base_fields.items():
            # Get or create new ImportFieldMetadata
            field = ImportFieldMetadata(
                field=field_instance,
                required=field_instance.required,
                help_text=help_texts.get(field_name, ""),
            )

            # Find the header sources for this field
            match field_instance:
                case SourceFieldSwitcher(fields=switch_fields):
                    # Containers a collections of ways to assign this field
                    for switch_field in switch_fields:
                        field.sources.append(
                            _get_headers(field_name, switch_field.widget)
                        )
                case FlatRelatedField(fields=related_fields):
                    # Defines a way to create related objects from a set of headers
                    temp_source = []
                    for new_fields in map(
                        partial(_get_headers, widget=field_instance.widget),
                        related_fields.keys(),
                    ):
                        temp_source.extend(new_fields)
                    field.sources.append(temp_source)
                case _:
                    fields = _get_headers(field_name, field_instance.widget)
                    field.sources.append(fields)

            # Add the field to the result
            import_fields[field_name] = field

        return import_fields
