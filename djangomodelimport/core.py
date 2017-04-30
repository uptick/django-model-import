import tablib

from .results import ImportResultRow, ImportResultSet


class ModelImporter:
    """ A base class which parses and processes a CSV import, and handles the priming of any required caches. """
    def __init__(self, modelvalidator):
        self.instances = []
        self.errors = []
        self.modelvalidator = modelvalidator

    def parse(self, data):
        # Parse the CSV
        dataset = tablib.Dataset()
        dataset.csv = data
        return dataset

    def process(self, data, commit=False):
        # Set up a cache context which will be filled by the Cached fields
        caches = ImportCache()

        # Parse the CSV
        dataset = self.parse(data)

        # Start processing
        importresult = ImportResultSet(import_headers=dataset.headers)
        for i, row in enumerate(dataset.dict, start=1):
            instance = None
            errors = []
            form = self.modelvalidator(row, caches)
            if form.is_valid():
                instance = form.save(commit=commit)
            else:
                errors = form.errors.items()

            importresult.append(i, row, errors, instance)

        return importresult
