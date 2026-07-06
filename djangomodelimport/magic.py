from collections.abc import Callable, Container, Hashable, Iterable
from typing import Any, ClassVar, cast

from django import forms
from django.core.exceptions import ValidationError
from django.db import models

from djangomodelimport.exceptions import InvalidWidgetException
from djangomodelimport.fields import (
    CachedChoiceField,
    FlatRelatedField,
    JSONField,
    SourceFieldSwitcher,
)
from djangomodelimport.loaders import CachedInstanceLoader
from djangomodelimport.types import Cache, Data
from djangomodelimport.widgets import CompositeLookupWidget, NamedSourceWidget

""" These mixins hold all the code that relates to our special fields (flat related, json, cached choice)
that just doesn't work without access to the form instance. """


class FlatRelatedFieldFormMixin(forms.ModelForm):
    def __init__(self, data: Data, *args: Any, **kwargs: Any) -> None:
        super().__init__(data, *args, **kwargs)

        self.flat_related_mapping: dict[str, str] = {}
        flat_related: dict[str, dict[str, Hashable]] = {}

        for field, fieldinstance in self.fields.items():
            # For each FlatRelatedField, save a mapping back to the field.
            if isinstance(fieldinstance, FlatRelatedField):
                flat_related[field] = {}
                for f in fieldinstance.fields.keys():
                    self.flat_related_mapping[f] = field

        # Tinker with data to combine flat fields into related objects.
        new_data = self.data.copy()
        for field, value in self.data.items():
            if field in self.flat_related_mapping:
                flat_related[self.flat_related_mapping[field]][field] = value
                del new_data[field]

        self.flat_data: Data = self.data
        self.data: Data = new_data

        for field, values in flat_related.items():
            mapped_values = dict(
                (cast("FlatRelatedField", self.fields[field]).fields[k]["to_field"], v)
                for k, v in values.items()
            )
            # Get or create the related instance.
            if getattr(self.instance, field + "_id") is None:
                instance = cast("FlatRelatedField", self.fields[field]).model(**mapped_values)
            else:
                instance = getattr(self.instance, field)
                for attr, value in mapped_values.items():
                    setattr(instance, attr, value)

            instance.save()  # NOTE: This gets fired during preview, but that's ok, since we wrap previews in a big rollback transaction.
            self.data[field] = instance

    def get_headers(self, given_headers: Container[str] | None = None) -> list[str]:
        headers = []
        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, FlatRelatedField):
                headers.extend(
                    f
                    for f in fieldinstance.fields.keys()
                    if given_headers is None or f in given_headers
                )
            else:
                headers.append(field)
        return headers

    def get_instance_values(
        self, instance: models.Model | None, headers: Iterable[str]
    ) -> list[Any]:
        instance_values = []
        for header in headers:
            if header in self.flat_related_mapping:
                rel_field_name = self.flat_related_mapping[header]
                rel = getattr(instance, rel_field_name)
                instance_values.append(
                    getattr(
                        rel,
                        cast("FlatRelatedField", self.fields[rel_field_name]).fields[header][
                            "to_field"
                        ],
                    )
                )
            else:
                try:
                    instance_values.append(getattr(instance, header))
                except ValueError:
                    # trying to access an m2m is not allowed before it has been saved
                    instance_values.append("")
                except AttributeError:
                    # trying to access a field that doesn't exist on the model definition, should we check for the field in _meta.exclude?
                    instance_values.append("")
        return instance_values

    # TODO:
    # def full_clean(self):
    #     """ Validate that required fields in FlatRelated fields have been provided. """
    #     super().full_clean()
    #     for field, fieldinstance in self.fields.items():
    #         if isinstance(fieldinstance, FlatRelatedField):
    #             for f in fieldinstance.fields:
    #                 import pdb; pdb.set_trace()
    #                 pass


class CachedChoiceFieldFormMixin[Model: models.Model]:
    fields: dict[str, forms.Field]
    caches: dict[str, Cache[Model]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field, fieldinstance in self.fields.items():
            # For each CachedInstanceLoader, prime the cache.
            if isinstance(fieldinstance, CachedChoiceField):
                if field not in self.caches:
                    self.caches[field] = CachedInstanceLoader(
                        fieldinstance.queryset, fieldinstance.to_field
                    )
                fieldinstance.set_cache(self.caches[field])

    def _get_validation_exclusions(self) -> set[str]:
        """We need to exclude any CachedChoiceFields from validation, as this
        causes a m * n queries where m is the number of relations, n is rows.
        """
        # pyrefly: ignore [missing-attribute]
        exclude = super()._get_validation_exclusions()
        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, CachedChoiceField):
                exclude.add(field)
        return exclude


class JSONFieldFormMixin[Model: models.Model]:
    fields: dict[str, forms.Field]
    get_initial_for_field: Callable[[forms.Field, str], Any]
    data: Data
    cleaned_data: dict[str, Any]
    add_prefix: Callable[[str], str]
    files: dict[str, Any]
    instance: Model
    add_error: Callable[[str, ValidationError], None]

    def _clean_fields(self) -> None:
        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the data dictionaries.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            if field.disabled:
                value = self.get_initial_for_field(field, name)
            elif isinstance(field.widget, forms.Widget):
                value = field.widget.value_from_datadict(
                    data=self.data, files=self.files, name=self.add_prefix(name)
                )
            else:
                raise InvalidWidgetException()

            try:
                if isinstance(field, forms.FileField):
                    initial = self.get_initial_for_field(field, name)
                    value = field.clean(value, initial)
                # PATCH
                if isinstance(field, JSONField):
                    initial = getattr(self.instance, name)
                    value = field.clean(value)
                    value = dict(initial, **value)  # this is the secret sauce.
                # ENDPATCH
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, f"clean_{name}"):
                    value = getattr(self, f"clean_{name}")()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)


class SourceFieldSwitcherMixin:
    base_fields: ClassVar[dict[str, forms.Field]]

    def __init__(self, data: Data, *args: Any, **kwargs: Any) -> None:
        """Swap out all `SourceFieldSwitcher` fields for actual fields."""
        for field_name, field_class in self.__class__.base_fields.items():
            if not isinstance(field_class, SourceFieldSwitcher):
                continue
            for actual_field in field_class.fields:
                if isinstance(actual_field.widget, NamedSourceWidget):
                    lookup = {actual_field.widget.source}
                elif isinstance(actual_field.widget, CompositeLookupWidget):
                    lookup = set(actual_field.widget.source)
                else:
                    lookup = {field_name}
                if lookup < set(data.keys()):
                    self.base_fields[field_name] = actual_field
                    break
        kwargs["data"] = data
        super().__init__(*args, **kwargs)
