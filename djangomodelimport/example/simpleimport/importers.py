from django import forms

from djangomodelimport import CachedChoiceField, ModelImportForm

from .models import Book


class BookImporter(ModelImportForm):
    name = forms.CharField()
    author = CachedChoiceField(queryset=Author.objects.all(), to_field='name')

    class Meta:
        model = Book
