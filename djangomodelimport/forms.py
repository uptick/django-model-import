from django import forms

from .magic import CachedChoiceFieldFormMixin, FlatRelatedFieldFormMixin, JSONFieldFormMixin


class ImporterModelForm(JSONFieldFormMixin, FlatRelatedFieldFormMixin, CachedChoiceFieldFormMixin, forms.ModelForm):
    """ Extends the ModelForm to prime our caches and tweaks the validation
    routines to ensure we are not doing too many queries with our cached fields.
    """
    def __init__(self, data, caches, author=None, *args, **kwargs):
        self.caches = caches
        self.author = author
        super().__init__(data, *args, **kwargs)

    # This improves preview performance but eliminates validation on uniqueness constraints
    # def validate_unique(self):
    #     pass
