from dateutil import parser

from django import forms
from django.forms.utils import from_current_timezone


class OneToOneField(forms.Field):
    """ Will create the related object if it does not yet exist. """
    instancecache = None

    def __init__(self, queryset, to_field=None, *args, **kwargs):
        self.queryset = queryset
        self.model = queryset.model
        self.to_field = to_field
        return super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        # Fast fail if no value provided
        value_exists = value and all(value)  # this will work for strings, and tuples of values
        if not value_exists:
            return None

        # Get or create the FK. Note that this will be running inside a transaction, which will
        # revert the creation in cases where commit = False.
        params = {self.to_field: value}
        try:
            cleaned_value, _ = self.model.objects.get_or_create(**params)
        except self.model.MultipleObjectsReturned:
            raise

        # Return it
        return cleaned_value


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
        except (self.model.DoesNotExist, self.model.MultipleObjectsReturned) as e:
            raise forms.ValidationError(
                "Unable to find object matching {}, {}".format(value, e)
            )

        # Return it
        if cleaned_value:
            return cleaned_value

        # Raise
        raise forms.ValidationError(
            "Could not find object matching {}".format(value)
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
        value = value.strip()
        try:
            result = parser.parse(value)
        except (TypeError, ValueError, OverflowError):
            raise forms.ValidationError(self.error_messages['invalid'], code='invalid')

        return from_current_timezone(result)
