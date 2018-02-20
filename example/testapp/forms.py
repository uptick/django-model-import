from django import forms


class TestImportForm(forms.Form):
    file_upload = forms.FileField()
