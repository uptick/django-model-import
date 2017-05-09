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


class TablibXSLXImportParser(ImportParser):
    def parse(self, data):
        # @todo work with soft_headings to map e.g. "Active" to "is_active"
        # on the modelvalidator
        dataset = tablib.Dataset()
        dataset.xslx = data
        return (dataset.headers, dataset.dict)
