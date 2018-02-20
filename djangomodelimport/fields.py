import json

from dateutil import parser

from django import forms
from django.forms.utils import from_current_timezone
from re import match


class FlatRelatedField(forms.Field):
    """ Will create the related object if it does not yet exist. """
    def __init__(self, queryset, fields=[], *args, **kwargs):
        self.queryset = queryset
        # TODO: If lookup key is provided, allow using it to look up value instead of only
        # retrieving it off the object itself.
        self.model = queryset.model
        self.fields = fields
        # Required is False, because this check gets passed down to the fields on the related instance.
        return super().__init__(required=False, *args, **kwargs)


class CachedChoiceField(forms.Field):
    """ Use a CachedChoiceField when you have a large table of choices, but
    expect the number of different values that occur to be relatively small.

    If you expect a larger number of different values, you might want to use a
    PreloadedChoiceField.
    """
    instancecache = None

    def __init__(self, queryset, to_field=None, *args, **kwargs):
        self.queryset = queryset
        self.model = queryset.model
        self.to_field = to_field
        return super().__init__(*args, **kwargs)

    def set_cache(self, cache):
        self.instancecache = cache

    def clean(self, value):
        value = super().clean(value)
        # Fast fail if no value provided
        value_exists = value and all(value)  # this will work for strings, and tuples of values
        if not value_exists:
            return None

        # Try and get the value from the loader
        try:
            cleaned_value = self.instancecache[value]
        except self.model.DoesNotExist:
            raise forms.ValidationError(
                "No %s matching '%s'." % (self.model._meta.verbose_name.title(), value)
            )
        except self.model.MultipleObjectsReturned:
            raise forms.ValidationError(
                "Multiple %s matching '%s'. Expected just one." % (self.model._meta.verbose_name_plural.title(), value)
            )

        # Return it
        if cleaned_value:
            return cleaned_value

        # Raise
        raise forms.ValidationError(
            "No %s matching '%s'." % (self.model._meta.verbose_name.title(), value)
        )


class PreloadedChoiceField(forms.Field):
    """ This will load all the possible values for this relationship once,
    to avoid hitting the database for each relationship in the import.
    """
    def clean(self, value):
        raise NotImplemented


class DateTimeParserField(forms.DateTimeField):
    """ A DateTime parser field that does it's best effort to understand. """
    def to_python(self, value):
        value = (value or '').strip()
        if value:
            try:
                return from_current_timezone(parser.parse(value, dayfirst=bool(match(r'^\d\d?.\d\d?.\d{4}$',value))))
            except (TypeError, ValueError, OverflowError):
                raise forms.ValidationError(self.error_messages['invalid'], code='invalid')

        else:
            return None


class JSONField(forms.Field):
    """ This lets you interact with a JSON or HStore type key/value field. """
    def __init__(self, **params):
        params['widget'] = params.get('widget', forms.Textarea)
        super().__init__(**params)

    def validate_json(value, is_serialized=False):
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
