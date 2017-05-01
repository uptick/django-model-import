from django import forms


class CachedChoiceField(forms.Field):
    """ Use a CachedChoiceField when you have a large table of choices, but
    expect the number of different values that occur to be relatively small.

    If you expect a larger number of different values, you might want to use a
    PreloadedChoiceField.
    """
    queryset = None
    to_field = None
    instancecache = None

    def __init__(self, queryset, to_field=None, *args, **kwargs):
        self.queryset = queryset
        self.to_field = to_field
        return super().__init__(*args, **kwargs)

    def set_cache(self, cache):
        self.instancecache = cache

    def clean(self, value):
        if value:
            cleaned_value = self.instancecache[value]
            if cleaned_value:
                return cleaned_value
            else:
                raise forms.ValidationError(
                    "Could not find object matching {}.".format(value)
                )


class PreloadedChoiceField(forms.Field):
    """ This will load all the possible values for this relationship once,
    to avoid hitting the database for each relationship in the import.
    """
    def clean(self, value):
        raise NotImplemented
