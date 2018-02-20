from django import forms

import djangomodelimport

from .models import Author, Book, Citation


class BookImporter(djangomodelimport.ImporterModelForm):
    name = forms.CharField()
    author = forms.ModelChoiceField(queryset=Author.objects.all(), to_field_name='name')

    class Meta:
        model = Book
        fields = (
            'name',
            'author',
        )


class BookImporterWithCache(djangomodelimport.ImporterModelForm):
    name = forms.CharField()
    author = djangomodelimport.CachedChoiceField(queryset=Author.objects.all(), to_field='name')

    class Meta:
        model = Book
        fields = (
            'name',
            'author',
        )


class CitationImporter(djangomodelimport.ImporterModelForm):
    name = forms.CharField()
    author = djangomodelimport.CachedChoiceField(queryset=Author.objects.all(), to_field='name')
    metadata = djangomodelimport.JSONField()

    class Meta:
        model = Citation
        fields = (
            'name',
            'author',
            'metadata',
        )
