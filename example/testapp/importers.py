from django import forms

import djangomodelimport

from .models import Author, Book


class BookImporter(djangomodelimport.ImporterModelForm):
    name = forms.CharField()
    author = djangomodelimport.CachedChoiceField(queryset=Author.objects.all(), to_field='name')

    class Meta:
        model = Book
        fields = (
            'name',
            'author',
        )
