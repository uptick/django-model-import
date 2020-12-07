import json
import re
from dateutil import parser

from django import forms
from django.forms.utils import from_current_timezone

from .widgets import JSONFieldWidget


class UseCacheMixin:
    instancecache = None

    def set_cache(self, cache):
        self.instancecache = cache


class FlatRelatedField(forms.Field):
    """ Will create the related object if it does not yet exist.

    All the magic happens in magic.py in FlatRelatedFieldFormMixin
    """
    def __init__(self, queryset, fields=[], *args, **kwargs):
        self.queryset = queryset
        # TODO: If lookup key is provided, allow using it to look up value instead of only
        # retrieving it off the object itself.
        self.model = queryset.model
        self.fields = fields
        # Required is False, because this check gets passed down to the fields on the related instance.
        return super().__init__(required=False, *args, **kwargs)


class CachedChoiceField(UseCacheMixin, forms.Field):
    """ Use a CachedChoiceField when you have a large table of choices, but
    expect the number of different values that occur to be relatively small.

    If you expect a larger number of different values, you might want to use a
    PreloadedChoiceField.
    """
    def __init__(self, queryset, to_field=None, none_if_missing=[], *args, **kwargs):
        self.queryset = queryset
        self.model = queryset.model
        self.to_field = to_field
        self.none_if_missing = none_if_missing
        return super().__init__(*args, **kwargs)

    def get_from_cache(self, value):
        return self.instancecache[value]

    def clean(self, value):
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
            return self.get_from_cache(value)
        except self.model.DoesNotExist:
            raise forms.ValidationError(
                "No %s matching '%s'." % (self.model._meta.verbose_name.title(), value)
            )
        except self.model.MultipleObjectsReturned:
            raise forms.ValidationError(
                "Multiple %s matching '%s'. Expected just one." % (self.model._meta.verbose_name_plural.title(), value)
            )


class PreloadedChoiceField(forms.Field):
    """ This will load all the possible values for this relationship once,
    to avoid hitting the database for each relationship in the import.
    """
    def clean(self, value):
        raise NotImplementedError


class DateTimeParserField(forms.DateTimeField):
    """ A DateTime parser field that does it's best effort to understand.

        Defaults to assuming little endian when there is ambiguity:
        - XX/XX/XX -> DD/MM/YY
        - XX/XX/XXXX -> DD/MM/YYYY

        Pass in `middle_endian=True` to get:
        - XX/XX/XX -> MM/DD/YY
        - XX/XX/XXXX -> MM/DD/YYYY

        If year is passed first, will always use big endian:
        - XXXX/XX/XX -> YYYY/MM/DD
    """
    def __init__(self, middle_endian=False, *args, **kwargs):
        self.middle_endian = middle_endian
        return super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = (value or '').strip()
        if value:
            try:
                dayfirst = not bool(re.match(r'^\d{4}.\d\d?.\d\d?', value)) and not self.middle_endian
                return from_current_timezone(parser.parse(value, dayfirst=dayfirst))
            except (TypeError, ValueError, OverflowError):
                raise forms.ValidationError(self.error_messages['invalid'], code='invalid')

        else:
            return None


class JSONField(forms.Field):
    """ This lets you store any fields prefixed by the field name into a JSON blob.

    For example, adding a field:
        metadata = JSONField()

    When the row is submitted with data that looks like this:
    id  name    author  metadata_rank   metadata_score
    -----------------------------------------------
        ding    bob     hello           twenty

    This field will return a JSON blob that looks like:
        {rank: "hello", score: "twenty"}
    """
    def __init__(self, **kwargs):
        kwargs['widget'] = kwargs.get('widget', JSONFieldWidget)
        kwargs['required'] = False
        kwargs['initial'] = dict
        super().__init__(**kwargs)

    def validate_json(self, value, is_serialized=False):
        # if empty
        if value is None or value == '' or value == 'null':
            value = '{}'

        # ensure valid JSON
        try:
            # convert strings to dictionaries
            if isinstance(value, str):
                dictionary = json.loads(value)

                # if serialized field, deserialize values
                if is_serialized and isinstance(dictionary, dict):
                    dictionary = dict((k, json.loads(v)) for k, v in dictionary.items())  # TODO: modify to use field's deserializer
            # if not a string we'll check at the next control if it's a dict
            else:
                dictionary = value
        except ValueError as e:
            raise forms.ValidationError(('Invalid JSON: {0}').format(e))

        # ensure is a dictionary
        if not isinstance(dictionary, dict):
            raise forms.ValidationError(('No lists or values allowed, only dictionaries'))

        # convert any non string object into string
        for key, value in dictionary.items():
            if isinstance(value, dict) or isinstance(value, list):
                dictionary[key] = json.dumps(value)
            if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
                if not is_serialized:  # Only convert if not from serializedfield
                    dictionary[key] = str(value).lower()

        return dictionary

    def to_python(self, value):
        return self.validate_json(value)

    def render(self, name, value, attrs=None):
        # return json representation of a meaningful value
        # doesn't show anything for None, empty strings or empty dictionaries
        if value and not isinstance(value, str):
            value = json.dumps(value, sort_keys=True, indent=4)
        return super().render(name, value, attrs)
