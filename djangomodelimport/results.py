class ImportResultSet:
    """ Hold all imported results. """
    import_headers = None
    results = None

    def __init__(self, import_headers):
        self.results = []
        self.import_headers = import_headers

    def append(self, index, row, errors, instance):
        self.results.append(
            ImportResultRow(self, index, row, errors, instance)
        )

    def get_import_headers(self):
        return self.import_headers

    def get_results(self):
        return self.results

    def get_errors(self):
        return [(row.linenumber, row.errors) for row in self.results if not row.is_valid()]


class ImportResultRow:
    """ Hold the result of an imported row. """
    resultset = None
    linenumber = None
    row = None
    errors = None
    instance = None

    def __init__(self, resultset, linenumber, row, errors, instance):
        self.resultset = resultset
        self.linenumber = linenumber
        self.row = row
        self.errors = errors
        self.instance = instance

    def get_instance_values(self):
        return [getattr(self.instance, header) for header in self.resultset.import_headers]

    def is_valid(self):
        return len(self.errors) == 0
