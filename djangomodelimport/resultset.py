class ImportResultSet:
    """ Hold all imported results. """
    results = None
    headers = None
    header_form = None
    created = 0
    updated = 0
    skipped = 0
    failed = 0

    def __init__(self, headers, header_form):
        self.results = []
        self.headers = headers
        self.header_form = header_form

    def __repr__(self):
        return f'ImportResultSet ({len(self.results)} rows, {len(self.get_errors())} errors)'

    def append(self, index, row, errors, instance, created):
        result_row = ImportResultRow(self, index, row, errors, instance, created)
        self.results.append(result_row)
        return result_row

    def get_import_headers(self):
        return self.header_form.get_headers(self.headers)

    def get_results(self):
        return self.results

    def get_errors(self):
        return [(row.linenumber, row.errors) for row in self.results if not row.is_valid()]

    def set_counts(self, created=created, updated=updated, skipped=skipped, failed=failed):
        self.created = created
        self.updated = updated
        self.skipped = skipped
        self.failed = failed

    def get_counts(self):
        return (self.created, self.updated, self.skipped, self.failed)


class ImportResultRow:
    """ Hold the result of an imported row. """
    resultset = None
    linenumber = None
    row = None
    errors = None
    instance = None
    created = None

    def __init__(self, resultset, linenumber, row, errors, instance, created):
        self.resultset = resultset
        self.linenumber = linenumber
        self.row = row
        self.errors = errors
        self.instance = instance
        self.created = created

    def __repr__(self):
        valid_str = "valid" if self.is_valid() else "invalid"
        mode_str = "create" if self.created else "update"
        res = self.get_instance_values() if self.is_valid() else self.errors
        sample = str([(k, v) for k, v in self.row.items()])[:100]
        return f'{self.linenumber}. [{valid_str}] [{mode_str}] ... {sample} ... {res}'

    def get_instance_values(self):
        return self.resultset.header_form.get_instance_values(self.instance, self.resultset.get_import_headers())

    def is_valid(self):
        return len(self.errors) == 0

    def get_errors(self):
        return self.errors
