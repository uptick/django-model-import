import operator

from django import forms


class CompositeLookupWidget(forms.Widget):
    def __init__(self, source, *args, **kwargs):
        self.source = source
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        getter = operator.itemgetter(*self.source)
        try:
            return getter(data)
        except KeyError as e:
            pass

    def value_omitted_from_data(self, data, files, name):
        getter = operator.itemgetter(*self.source)
        try:
            getter(data)
            return False
        except KeyError as e:
            return True
