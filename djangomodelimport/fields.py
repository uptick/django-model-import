import datetime
import json
import re
from collections.abc import Collection
from typing import Any, TypedDict

from dateutil import parser

from django import forms
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.forms.utils import from_current_timezone

from djangomodelimport.types import Cache
from djangomodelimport.widgets import JSONFieldWidget


class UseCacheMixin[Model: models.Model]:
    instancecache: Cache[Model] | None = None

    def set_cache(self, cache: Cache[Model]) -> None:
        self.instancecache = cache


class FieldMapping(TypedDict, total=False):
    to_field: str


class FlatRelatedField[Model: models.Model](forms.Field):
    """Will create the related object if it does not yet exist.

    All the magic happens in magic.py in FlatRelatedFieldFormMixin
    """

    def __init__(
        self,
        queryset: QuerySet[Model],
        fields: dict[str, FieldMapping] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.queryset: QuerySet[Model] = queryset
        # TODO: If lookup key is provided, allow using it to look up value instead of only
        # retrieving it off the object itself.
        self.model: type[Model] = queryset.model
        self.fields: dict[str, FieldMapping] = fields or {}
        # Required is False, because this check gets passed down to the fields on the related instance.
        super().__init__(*args, required=False, **kwargs)


class CachedChoiceField[Model: models.Model](UseCacheMixin, forms.Field):
    """Use a CachedChoiceField when you have a large table of choices, but
    expect the number of different values that occur to be relatively small.

    If you expect a larger number of different values, you might want to use a
    PreloadedChoiceField.
    """

    def __init__(
        self,
        queryset: QuerySet[Model],
        to_field: str | Collection[str] = "id",
        none_if_missing: Collection[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.queryset: QuerySet[Model] = queryset
        self.model: type[Model] = queryset.model
        self._model_verbose_name: str = (
            self.model._meta.verbose_name or self.model.__name__
        ).title()
        self._model_verbose_name_plural: str = (
            self.model._meta.verbose_name_plural or self.model.__name__ + "s"
        ).title()
        self.to_field: str | Collection[str] = to_field
        self.none_if_missing: Collection[str] = none_if_missing or []
        super().__init__(*args, **kwargs)

    def get_from_cache(self, value: Any) -> Model | ObjectDoesNotExist | MultipleObjectsReturned:
        if self.instancecache is None:
            raise self.model.DoesNotExist("No cache set")
        return self.instancecache[value]

    def clean(self, value: Any) -> Model | None:
        value = super().clean(value)

        # Fast fail if no value provided
        if not value:
            return None

        # Composite lookups are fine to have blank values in them e.g. for a firstname/lastname
        # lookup, it's fine to have ('Jenny', '').
        # However, in some situations we need some fields to be set to be able to do the lookup.
        # If they are missing then the lookup is blank.
        # @todo Think about whether this should be a validation error if self.required is True
        if self.none_if_missing:
            for field_pos in self.none_if_missing:
                if not value[field_pos]:
                    return None

        # Try and get the value from the loader
        try:
            # pyrefly: ignore [bad-return]
            return self.get_from_cache(value)
        except self.model.DoesNotExist as err:
            raise forms.ValidationError(
                f"No {self._model_verbose_name} matching '{value}'."
            ) from err
        except self.model.MultipleObjectsReturned as err:
            raise forms.ValidationError(
                f"Multiple {self._model_verbose_name_plural} matching '{value}'. Expected just one."
            ) from err


class PreloadedChoiceField(forms.Field):
    """This will load all the possible values for this relationship once,
    to avoid hitting the database for each relationship in the import.
    """

    def clean(self, value: Any) -> Any:
        raise NotImplementedError


class DateTimeParserField(forms.DateTimeField):
    """A DateTime parser field that does it's best effort to understand.

    Defaults to assuming little endian when there is ambiguity:
    - XX/XX/XX -> DD/MM/YY
    - XX/XX/XXXX -> DD/MM/YYYY

    Pass in `middle_endian=True` to get:
    - XX/XX/XX -> MM/DD/YY
    - XX/XX/XXXX -> MM/DD/YYYY

    If year is passed first, will always use big endian:
    - XXXX/XX/XX -> YYYY/MM/DD
    """

    def __init__(self, middle_endian: bool = False, *args: Any, **kwargs: Any) -> None:
        self.middle_endian: bool = middle_endian
        super().__init__(*args, **kwargs)

    def to_python(self, value: str | None) -> datetime.datetime | None:
        value = (value or "").strip()
        if value:
            try:
                dayfirst = (
                    not bool(re.match(r"^\d{4}.\d\d?.\d\d?", value)) and not self.middle_endian
                )
                return from_current_timezone(parser.parse(value, dayfirst=dayfirst))
            except (TypeError, ValueError, OverflowError) as err:
                raise forms.ValidationError(self.error_messages["invalid"], code="invalid") from err

        else:
            return None


class JSONField(forms.Field):
    """This lets you store any fields prefixed by the field name into a JSON blob.

    For example, adding a field:
        metadata = JSONField()

    When the row is submitted with data that looks like this:
    id  name    author  metadata_rank   metadata_score
    -----------------------------------------------
        ding    bob     hello           twenty

    This field will return a JSON blob that looks like:
        {rank: "hello", score: "twenty"}
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs["widget"] = kwargs.get("widget", JSONFieldWidget)
        kwargs["required"] = False
        kwargs["initial"] = dict
        super().__init__(**kwargs)

    def validate_json(self, value: str | None, is_serialized: bool = False) -> dict[str, Any]:
        # if empty
        if value is None or value == "" or value == "null":
            value = "{}"

        # ensure valid JSON
        try:
            # convert strings to dictionaries
            if isinstance(value, str):
                dictionary = json.loads(value)

                # if serialized field, deserialize values
                if is_serialized and isinstance(dictionary, dict):
                    dictionary = dict(
                        (k, json.loads(v)) for k, v in dictionary.items()
                    )  # TODO: modify to use field's deserializer
            # if not a string we'll check at the next control if it's a dict
            else:
                dictionary = value
        except ValueError as err:
            raise forms.ValidationError(f"Invalid JSON: {err}") from err

        # ensure is a dictionary
        if not isinstance(dictionary, dict):
            raise forms.ValidationError("No lists or values allowed, only dictionaries")

        # convert any non string object into string
        for key, value in dictionary.items():
            if isinstance(value, dict) or isinstance(value, list):
                dictionary[key] = json.dumps(value)
            if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
                if not is_serialized:  # Only convert if not from serializedfield
                    dictionary[key] = str(value).lower()

        return dictionary

    def to_python(self, value: str | None) -> dict[str, Any] | None:
        return self.validate_json(value)

    def render(self, name: str, value: str, attrs: Any = None) -> Any:
        # return json representation of a meaningful value
        # doesn't show anything for None, empty strings or empty dictionaries
        if value and not isinstance(value, str):
            value = json.dumps(value, sort_keys=True, indent=4)
        return value


class SourceFieldSwitcher(forms.Field):
    def __init__(self, *fields: forms.Field, **kwargs: Any) -> None:
        self.fields: tuple[forms.Field, ...] = fields
        super().__init__(**kwargs)
