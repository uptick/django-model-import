from django.urls import reverse
from django.views.generic.edit import FormView

import djangomodelimport

from .forms import TestImportForm
from .importers import CitationImporter


class TestImportView(FormView):
    template_name = 'testapp/testimport.html'
    form_class = TestImportForm

    def form_valid(self, form):
        thefile = form.cleaned_data['file_upload']
        contents = thefile.read().decode('utf8', 'ignore')

        parser = djangomodelimport.TablibCSVImportParser(CitationImporter)
        headers, rows = parser.parse(contents)

        importer = djangomodelimport.ModelImporter(CitationImporter)
        preview = importer.process(headers, rows, commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        print(errors)
        results = preview.get_results()
        print(results)

        # importresult = importer.process(headers, rows, commit=True)
        # res = importresult.get_results()

    def get_success_url(self):
        return reverse('start') + '?result=OK'
