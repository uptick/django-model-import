import json

from django.core.exceptions import ValidationError
from django.forms import FileField

from .fields import JSONField


""" These mixins hold all the code that relates to our special fields (flat related, json, cached choice)
that just doesn't work without access to the form instance. """


class FlatRelatedFieldFormMixin:
    pass
    # TODO:
    # def full_clean(self):
    #     """ Validate that required fields in FlatRelated fields have been provided. """
    #     super().full_clean()
    #     for field, fieldinstance in self.fields.items():
    #         if isinstance(fieldinstance, FlatRelatedField):
    #             for f in fieldinstance.fields:
    #                 import pdb; pdb.set_trace()
    #                 pass


class CachedChoiceFieldFormMixin:
    pass


class JSONFieldFormMixin:
    def _clean_fields(self):
        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the data dictionaries.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            if field.disabled:
                value = self.get_initial_for_field(field, name)
            else:
                value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
            try:
                if isinstance(field, FileField):
                    initial = self.get_initial_for_field(field, name)
                    value = field.clean(value, initial)
                # PATCH
                if isinstance(field, JSONField):
                    initial = getattr(self.instance, name)
                    value = field.clean(value)
                    if isinstance(value, str):  # sqlite non-jsonfield support
                        value = json.loads(value.replace("'", '"'))
                    if isinstance(initial, str):  # sqlite non-jsonfield support
                        initial = json.loads(initial.replace("'", '"'))
                    value = dict(initial, **value)  # this is the secret sauce.
                    value = json.dumps(value)
                # ENDPATCH
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, 'clean_%s' % name):
                    value = getattr(self, 'clean_%s' % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)
