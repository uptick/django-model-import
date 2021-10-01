from django.core.exceptions import ValidationError
from django.forms import FileField

from .fields import CachedChoiceField, FlatRelatedField, JSONField, UseCacheMixin
from .loaders import CachedInstanceLoader

""" These mixins hold all the code that relates to our special fields (flat related, json, cached choice)
that just doesn't work without access to the form instance. """


class FlatRelatedFieldFormMixin:
    def __init__(self, data, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        self.flat_related_mapping = {}
        flat_related = {}

        for field, fieldinstance in self.fields.items():
            # For each FlatRelatedField, save a mapping back to the field.
            if isinstance(fieldinstance, FlatRelatedField):
                flat_related[field] = {}
                for f in fieldinstance.fields.keys():
                    self.flat_related_mapping[f] = field

        # Tinker with data to combine flat fields into related objects.
        new_data = self.data.copy()
        for field, value in self.data.items():
            if field in self.flat_related_mapping:
                flat_related[self.flat_related_mapping[field]][field] = value
                del new_data[field]

        self.flat_data = self.data
        self.data = new_data

        for field, values in flat_related.items():
            mapped_values = dict((self.fields[field].fields[k]['to_field'], v) for k, v in values.items())
            # Get or create the related instance.
            if getattr(self.instance, field + '_id') is None:
                instance = self.fields[field].model(**mapped_values)
            else:
                instance = getattr(self.instance, field)
                for attr, value in mapped_values.items():
                    setattr(instance, attr, value)

            instance.save()  # NOTE: This gets fired during preview, but that's ok, since we wrap previews in a big rollback transaction.
            self.data[field] = instance

    def get_headers(self, given_headers=None):
        headers = []
        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, FlatRelatedField):
                headers.extend(f for f in fieldinstance.fields.keys() if given_headers is None or f in given_headers)
            else:
                headers.append(field)
        return headers

    def get_instance_values(self, instance, headers):
        instance_values = []
        for header in headers:
            if header in self.flat_related_mapping:
                rel_field_name = self.flat_related_mapping[header]
                rel = getattr(instance, rel_field_name)
                instance_values.append(getattr(rel, self.fields[rel_field_name].fields[header]['to_field']))
            else:
                try:
                    instance_values.append(getattr(instance, header))
                except ValueError:
                    instance_values.append('')  # trying to access an m2m is not allowed before it has been saved
                except AttributeError:
                    instance_values.append('')  # trying to access a field that doesn't exist on the model definition, should we check for the field in _meta.exclude?
        return instance_values

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
    def __init__(self, data, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        for field, fieldinstance in self.fields.items():
            # For each CachedInstanceLoader, prime the cache.
            if isinstance(fieldinstance, UseCacheMixin):
                if field not in self.caches:
                    self.caches[field] = CachedInstanceLoader(fieldinstance.queryset, fieldinstance.to_field)
                fieldinstance.set_cache(self.caches[field])

    def _get_validation_exclusions(self):
        """ We need to exclude any CachedChoiceFields from validation, as this
        causes a m * n queries where m is the number of relations, n is rows.
        """
        exclude = []
        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, CachedChoiceField):
                exclude.append(field)
        return exclude


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
                    value = dict(initial, **value)  # this is the secret sauce.
                # ENDPATCH
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, 'clean_%s' % name):
                    value = getattr(self, 'clean_%s' % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)
