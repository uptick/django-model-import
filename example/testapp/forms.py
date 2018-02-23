from django import forms

from djangomodelimport import JSONField

from .models import Citation


class TestImportForm(forms.Form):
    file_upload = forms.FileField()
    save = forms.BooleanField(required=False)


class CitationForm(forms.ModelForm):
    metadata = JSONField()

    class Meta:
        fields = [
            'name',
            'author',
            'metadata',
        ]
        model = Citation
