import tablib
from django.forms import modelform_factory

from .caches import SimpleDictCache
from .results import ImportResultRow, ImportResultSet


class ModelImporter:
    """ A base class which parses and processes a CSV import, and handles the priming of any required caches. """
    def __init__(self, modelimportform):
        self.instances = []
        self.errors = []
        self.modelimportform = modelimportform
        self.model = modelimportform.Meta.model

    def parse(self, data):
        """ Parse the imported data. """
        dataset = tablib.Dataset()
        dataset.csv = data
        return dataset

    def get_modelimport_form_class(self, fields):
        """ Return a modelform for use with this data.

        We use a modelform_factory to dynamically limit the fields on the import,
        otherwise the absence of a value can be taken as false for boolean fields,
        where as we want the model's default value to kick in.
        """
        return modelform_factory(
            self.model,
            form=self.modelimportform,
            fields=fields,
        )

    def process(self, data, commit=False):
        # Set up a cache context which will be filled by the Cached fields
        caches = SimpleDictCache()

        # Parse the CSV
        dataset = self.parse(data)

        # Prepare
        headers = dataset.headers
        ModelImportForm = self.get_modelimport_form_class(fields=headers)
        importresult = ImportResultSet(import_headers=headers)

        # Start processing
        for i, row in enumerate(dataset.dict, start=1):
            instance = None
            errors = []

            form = ModelImportForm(row, caches)
            if form.is_valid():
                instance = form.save(commit=commit)
            else:
                errors = form.errors.items()

            importresult.append(i, row, errors, instance)

        return importresult
