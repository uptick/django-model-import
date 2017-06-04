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
        except KeyError:
            pass

    def value_omitted_from_data(self, data, files, name):
        # if any of the fields are blank or do not appear in the lookup, assume
        # they are ommitted from the dataset
        return not all([data.get(source_field, '') for source_field in self.source])
