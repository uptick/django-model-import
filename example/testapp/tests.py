from testapp.importers import BookImporter, BookImporterWithCache
from testapp.models import Author, Book

from django.test import TestCase

import djangomodelimport


sample_csv_1 = """id,name,author
,How to be awesome,Aidan Lister
,How not to be awesome,Bill
"""

sample_csv_2 = """id,name,author
111,Howdy,Author Joe
333,Goody,Author Bill
"""

sample_csv_5 = """id,name,author
,How to be awesome,Aidan Lister
,How to be really awesome,Aidan Lister
,How to be the best,Aidan Lister
,How to be great,Aidan Lister
,How to be so good,Aidan Lister
,How to be better than that,Aidan Lister
,How not to be awesome,Bill
"""


class DMICoreTestCase(TestCase):
    def setUp(self):
        pass

    def test_importer(self):
        Author.objects.create(name='Aidan Lister')
        Author.objects.create(name='Bill')

        parser = djangomodelimport.TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_1)

        importer = djangomodelimport.ModelImporter(BookImporter)
        preview = importer.process(headers, rows, commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(errors, [])

        importresult = importer.process(headers, rows, commit=True)
        res = importresult.get_results()

        # Make sure we get two rows
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].instance.author.name, 'Aidan Lister')

    def test_importer_no_insert(self):
        parser = djangomodelimport.TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_1)

        importer = djangomodelimport.ModelImporter(BookImporter)
        preview = importer.process(headers, rows, allow_insert=False, commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0], (1, [('', 'Creating new rows is not permitted')]))

    def test_importer_no_update(self):
        a1 = Author.objects.create(name='Aidan Lister')
        a2 = Author.objects.create(name='Bill')

        Book.objects.create(id=111, name='Hello', author=a1)
        Book.objects.create(id=333, name='Goodbye', author=a2)

        parser = djangomodelimport.TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_2)

        importer = djangomodelimport.ModelImporter(BookImporter)
        preview = importer.process(headers, rows, allow_update=False, limit_to_queryset=Book.objects.all(), commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0], (1, [('', 'Updating existing rows is not permitted')]))

    def test_importer_limited_queryset(self):
        a1 = Author.objects.create(name='Author Joe')
        a2 = Author.objects.create(name='Author Bill')

        b1 = Book.objects.create(id=111, name='Hello', author=a1)
        Book.objects.create(id=333, name='Goodbye', author=a2)

        parser = djangomodelimport.TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_2)

        importer = djangomodelimport.ModelImporter(BookImporter)
        preview = importer.process(headers, rows, allow_update=True, limit_to_queryset=Book.objects.filter(id=b1.id), commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0], (2, [('', 'Book 333 cannot be updated.')]))


class CachedChoiceFieldTestCase(TestCase):
    def setUp(self):
        pass

    def test_importer(self):
        Author.objects.create(name='Aidan Lister')
        Author.objects.create(name='Bill')

        parser = djangomodelimport.TablibCSVImportParser(BookImporterWithCache)
        headers, rows = parser.parse(sample_csv_5)

        importer = djangomodelimport.ModelImporter(BookImporterWithCache)

        # @todo check number of queries
        importresult = importer.process(headers, rows, commit=True)
        res = importresult.get_results()

        # Make sure there's no errors
        errors = importresult.get_errors()
        self.assertEqual(errors, [])

        # Make sure we get two rows
        self.assertEqual(len(res), 7)
        self.assertEqual(res[0].instance.author.name, 'Aidan Lister')
