class BaseImportParser:
    def __init__(self, modelvalidator):
        """ We provide the modelvalidator to get some Meta information about
        valid fields, and any soft headings.
        """
        self.modelvalidator = modelvalidator

    def get_soft_headings(self):
        # Soft headings are used to provide similar heading suggestions
        # and look like this: {the field name: [list of other possible names] }
        # eg.
        #
        # soft_headings = {
        #   'type': ['Asset Type'],
        # }
        header_map = {}
        if hasattr(self.modelvalidator, 'ImporterMeta'):
            if hasattr(self.modelvalidator.ImporterMeta, 'soft_headings'):
                importer_softheadings = self.modelvalidator.ImporterMeta.soft_headings

                for renameto in importer_softheadings:  # new column name
                    for renamefrom in importer_softheadings[renameto]:  # old column name
                        header_map[renamefrom.lower()] = renameto.lower()
        return header_map

    def parse(self, data):
        """ Parsers should return a tuple containing (headings, data)

        They should also take a dictionary of soft_headings which map
        similar names to actual headings.
        """
        raise NotImplementedError


class TablibBaseImportParser(BaseImportParser):
    def __init__(self, *args, **kwargs):
        # Inline import, so tablib is only grabbed if/when this Parser is instanciated.
        from tablib import Dataset
        self.dataset_class = Dataset
        super().__init__(*args, **kwargs)


class TablibCSVImportParser(TablibBaseImportParser):
    def parse(self, data):
        dataset = self.dataset_class()
        dataset.csv = data

        header_map = self.get_soft_headings()

        # Make all our headings lowercase and sub in soft headings
        for col_id, header in enumerate(dataset.headers):  # replace it in headers if found
            header_name = header.strip().lower()
            dataset.headers[col_id] = header_name
            if header_name in header_map.keys():
                dataset.headers[col_id] = header_map[header_name]

        return (dataset.headers, dataset.dict)


class TablibXLSXImportParser(TablibBaseImportParser):
    def parse(self, data):
        dataset = self.dataset_class()
        # TODO: This does not currently work, as dataset.xlsx cannot be set.
        # http://docs.python-tablib.org/en/latest/api/#tablib.Dataset.xlsx
        # We can wait for it to be supported, or in the meantime, use this converter:
        # https://github.com/dilshod/xlsx2csv
        dataset.xlsx = data  # CANNOT SET
        return (dataset.headers, dataset.dict)
