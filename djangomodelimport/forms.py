from collections import defaultdict

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

        for field, fieldinstance in self.fields.items():
            # For each CachedInstanceLoader, prime the cache.
            if isinstance(fieldinstance, CachedChoiceField):
                if field not in caches:
                    caches[field] = CachedInstanceLoader(fieldinstance.queryset, fieldinstance.to_field)
                fieldinstance.set_cache(caches[field])
            # For each FlatRelatedField, save a mapping back to the field.
            if isinstance(fieldinstance, FlatRelatedField):
                for f in fieldinstance.fields:
                    self.flat_related_mapping[f[0]] = field

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

    def get_headers(self):
        headers = []
        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, FlatRelatedField):
                headers.extend(f[0] for f in fieldinstance.fields)
            else:
                headers.append(field)
        return headers

    def is_valid(self):
        # Tinker with data to combine flat fields back into related objects.
        flat_related = defaultdict(dict)
        new_data = self.data.copy()
        for field, value in self.data.items():
            if field in self.flat_related_mapping:
                flat_related[self.flat_related_mapping[field]][field] = value
                del new_data[field]
        self.data = new_data

        for field, values in flat_related.items():
            to_fields = dict(self.fields[field].fields)
            mapped_values = dict((to_fields[k], v) for k, v in values.items())
            # Get or create the related instance.
            if getattr(self.instance, field + '_id') is None:
                instance = self.fields[field].model(**mapped_values)
            else:
                instance = getattr(self.instance, field)
                for attr, value in mapped_values.items():
                    setattr(instance, attr, value)
            instance.save()
            self.data[field] = instance

        return super().is_valid()
