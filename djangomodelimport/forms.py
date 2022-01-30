from collections import defaultdict

from django import forms

from .magic import CachedChoiceFieldFormMixin, FlatRelatedFieldFormMixin, JSONFieldFormMixin


class ImporterModelForm(JSONFieldFormMixin, FlatRelatedFieldFormMixin, CachedChoiceFieldFormMixin, forms.ModelForm):
    """ Extends the ModelForm to prime our caches and tweaks the validation
    routines to ensure we are not doing too many queries with our cached fields.
    """
    def __init__(self, data, caches, author=None, *args, **kwargs):
        self.caches = caches
        self.author = author
        self._warnings = defaultdict(list)
        super().__init__(data, *args, **kwargs)

    def add_warning(self, field: str, warning: str):
        # Mimic django form behaviour for errors
        if not field:
            field = '__all__'

        self._warnings[field].append(warning)

    @property
    def warnings(self):
        return dict(self._warnings)

    # This improves preview performance but eliminates validation on uniqueness constraints
    # def validate_unique(self):
    #     pass
