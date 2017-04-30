from django import forms


class ModelImportForm(forms.ModelForm):
    """ Extends the ModelForm to prime our caches and tweaks the validation
    routines to ensure we are not doing too many queries with our cached fields.
    """
    def __init__(self, data, caches, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        for field, fieldinstance in self.fields.items():
            if isinstance(fieldinstance, CachedChoiceField):
                if field not in caches:
                    caches[field] = CachedInstanceLoader(fieldinstance.queryset, fieldinstance.to_field)
                fieldinstance.set_cache(caches[field])

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
