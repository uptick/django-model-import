from django import forms

from .fields import CachedChoiceField, FlatRelatedField
from .loaders import CachedInstanceLoader


class ImporterModelForm(forms.ModelForm):
    """ Extends the ModelForm to prime our caches and tweaks the validation
    routines to ensure we are not doing too many queries with our cached fields.
    """
    def __init__(self, data, caches, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        self.flat_related_mapping = {}
        flat_related = {}

        for field, fieldinstance in self.fields.items():
            # For each CachedInstanceLoader, prime the cache.
            if isinstance(fieldinstance, CachedChoiceField):
                if field not in caches:
                    caches[field] = CachedInstanceLoader(fieldinstance.queryset, fieldinstance.to_field)
                fieldinstance.set_cache(caches[field])
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
            instance.save()
            self.data[field] = instance

    def validate_unique(self):
        pass

    def _get_validation_exclusions(self):
        """ We need to exclude any CachedChoiceFields from validation, as this
        causes a m * n queries where m is the number of relations, n is rows.
        """
        exclude = []
        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, CachedChoiceField):
                exclude.append(field)

        return exclude

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
                instance_values.append(getattr(instance, header))
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
