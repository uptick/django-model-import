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
        # We need to tell django-model-import to import data into "metadata"
        # even if it's not in the table headings, because it will look like metadata_xxx, metadata_yyy
        virtual_fields = ('metadata', )
