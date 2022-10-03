from django import forms

import djangomodelimport

from .models import Author, Book, Citation, Company, Contact


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


class CompanyImporter(djangomodelimport.ImporterModelForm):
    primary_contact = djangomodelimport.FlatRelatedField(
        queryset=Contact.objects.all(),
        fields={
            'contact_name': {'to_field': 'name', 'required': True},
            'email': {'to_field': 'email'},
            'mobile': {'to_field': 'mobile'},
            'address': {'to_field': 'address'},
        },
    )

    class Meta:
        model = Company
        fields = (
            'name',
            'primary_contact',
        )
