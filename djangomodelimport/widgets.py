import operator

from django import forms


class CompositeLookupWidget(forms.Widget):
    def __init__(self, keys, *args, **kwargs):
        self.keys = keys
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        getter = operator.itemgetter(*self.keys)
        try:
            val = getter(data)
        except KeyError as e:
            val = None
        return val
