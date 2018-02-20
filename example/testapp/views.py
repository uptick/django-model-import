from django.urls import reverse
from django.views.generic.edit import CreateView, FormView

import djangomodelimport

from .forms import CitationForm, TestImportForm
from .importers import CitationImporter
from .models import Citation


class TestImportView(FormView):
    template_name = 'testapp/testimport.html'
    form_class = TestImportForm

    def form_valid(self, form):
        thefile = form.cleaned_data['file_upload']
        contents = thefile.read().decode('utf8', 'ignore')

        parser = djangomodelimport.TablibCSVImportParser(CitationImporter)
        headers, rows = parser.parse(contents)

        importer = djangomodelimport.ModelImporter(CitationImporter)

        commit = form.cleaned_data['save']
        results = importer.process(headers, rows, commit=commit)

        context = self.get_context_data(results=results)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'citations': Citation.objects.all(),
        })
        return ctx


class CitationCreateView(CreateView):
    template_name = 'testapp/create.html'
    form_class = CitationForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'citations': Citation.objects.all(),
        })
        return ctx

    def get_success_url(self):
        return reverse('create')
