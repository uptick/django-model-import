import tablib


class ImportParser:
    def __init__(self, modelvalidator):
        """ We provide the modelvalidator to get some Meta information about
        valid fields, and any soft headings.
        """
        self.modelvalidator = modelvalidator

    def parse(self, data):
        """ Parsers should return a tuple containing (headings, data)

        They should also take a dictionary of soft_headings which map
        similar names to actual headings.
        """
        raise NotImplemented


class TablibCSVImportParser(ImportParser):
    def parse(self, data):
        # @todo work with soft_headings to map e.g. "Active" to "is_active"
        # on the modelvalidator
        dataset = tablib.Dataset()
        dataset.csv = data
        return (dataset.headers, dataset.dict)


class TablibXLSXImportParser(ImportParser):
    def parse(self, data):
        # @todo work with soft_headings to map e.g. "Active" to "is_active"
        # on the modelvalidator
        dataset = tablib.Dataset()
        # TODO: This does not currently work, as dataset.xlsx cannot be set.
        # http://docs.python-tablib.org/en/latest/api/#tablib.Dataset.xlsx
        # We can wait for it to be supported, or in the meantime, use this converter:
        # https://github.com/dilshod/xlsx2csv
        dataset.xlsx = data  # CANNOT SET
        return (dataset.headers, dataset.dict)
