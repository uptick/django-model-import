import operator

from django import forms


class DisplayChoiceWidget(forms.Widget):
    """ This widget is helpful when the value being uploaded by the customer is the
    display choice, not the value. This widget will map the display choice back to the value.
    """
    choices = None
    display_to_choice_map = None

    def flip_enum(self, choices):
        return dict(zip(dict(choices).values(), dict(choices).keys()))

    def __init__(self, choices, *args, **kwargs):
        self.choices = choices
        self.display_to_choice_map = self.flip_enum(choices)
        return super().__init__(choices, *args, **kwargs)

    def value_from_datadict(self, data, files, name):
        """
        Given a dictionary of data and this widget's name, return the value
        of this widget or None if it's not provided.
        """
        val = data.get(name)
        return self.display_to_choice_map.get(val)

    def format_value(self, value):
        return self.choices.get(value)


class CompositeLookupWidget(forms.Widget):
    def __init__(self, source, *args, **kwargs):
        self.source = source
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        getter = operator.itemgetter(*self.source)
        try:
            return getter(data)
        except KeyError:
            pass

    def value_omitted_from_data(self, data, files, name):
        for field_name in self.source:
            if field_name not in data:
                return True
        return False


class JSONFieldWidget(forms.Widget):
    template_name = 'django/forms/widgets/textarea.html'

    def render(self, name, value, attrs=None, renderer=None):
        return ''

    def value_omitted_from_data(self, data, files, name):
        return not any([key.startswith(name) for key in data.keys()])

    def value_from_datadict(self, data, files, name):
        extra_fields = {}
        for f in data.keys():
            if f.startswith(name):
                new_field = f[len(name) + 1:]
                extra_fields[new_field] = data[f]
        return extra_fields
