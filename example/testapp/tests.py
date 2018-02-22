from testapp.importers import BookImporter, BookImporterWithCache, CitationImporter
from testapp.models import Author, Book, Citation

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

sample_csv_3 = """id,author,name,metadata_isbn,metadata_doi
,Fred Johnson,Starburst,ISBN333,doi:111
,Fred Johnson,Gattica,ISBN666,doi:222
"""

sample_csv_4 = """id,author,name,metadata_xxx,metadata_yyy,metadata_doi
10,Fred Johnson,Starburst,qqqq,www,valid_doi1
20,Fred Johnson,Gattica,aaa,bbb,valid_doi2
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

        # Check for only two queries (one to look up Bill, another to look up Aidan Lister)
        # Expected query log:
        # SAVEPOINT "s140735624082240_x2"
        # SAVEPOINT "s140735624082240_x3"
        # SELECT "testapp_author"."id", "testapp_author"."name" FROM "testapp_author" WHERE "testapp_author"."name" = 'Aidan Lister'
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How to be awesome', 2)
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How to be really awesome', 2)
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How to be the best', 2)
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How to be great', 2)
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How to be so good', 2)
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How to be better than that', 2)
        # SELECT "testapp_author"."id", "testapp_author"."name" FROM "testapp_author" WHERE "testapp_author"."name" = 'Bill'
        # INSERT INTO "testapp_book" ("name", "author_id") VALUES ('How not to be awesome', 3)
        # RELEASE SAVEPOINT "s140735624082240_x3"
        # RELEASE SAVEPOINT "s140735624082240_x2"
        with self.assertNumQueries(13):
            importresult = importer.process(headers, rows, commit=True)

        res = importresult.get_results()

        # Make sure there's no errors
        errors = importresult.get_errors()
        self.assertEqual(errors, [])

        # Make sure we get two rows
        self.assertEqual(len(res), 7)
        self.assertEqual(res[0].instance.author.name, 'Aidan Lister')


class DMIJSONFieldTestCase(TestCase):
    def setUp(self):
        pass

    def test_import(self):
        Author.objects.get_or_create(name="Fred Johnson")

        parser = djangomodelimport.TablibCSVImportParser(CitationImporter)
        headers, rows = parser.parse(sample_csv_3)

        importer = djangomodelimport.ModelImporter(CitationImporter)
        importresult = importer.process(headers, rows, commit=True)

        # Make sure there's no errors
        errors = importresult.get_errors()
        self.assertEqual(errors, [])

        res = importresult.get_results()

        # Make sure we get two rows
        expected_json = {'isbn': 'ISBN333', 'doi': 'doi:111'}
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].instance.metadata, expected_json)

        # Really check it worked
        cite = Citation.objects.get(pk=res[0].instance.pk)
        self.assertEqual(cite.metadata, expected_json)

    def test_fields_get_merged(self):
        (author, created) = Author.objects.get_or_create(name="Fred Johnson")
        c1 = Citation.objects.create(
            id=10,
            author=author,
            name='Diff1',
            metadata={
                "doi": "some doi",
                "isbn": "hello",
            },
        )
        c2 = Citation.objects.create(
            id=20,
            author=author,
            name='Diff2',
            metadata={
                "doi": "another doi",
                "isbn": "mate",
            },
        )

        # id,author,name,metadata_xxx,metadata_yyy,metadata_doi
        # 10,Fred Johnson,Starburst,qqqq,www,valid_doi1
        # 20,Fred Johnson,Gattica,aaa,,valid_doi2
        parser = djangomodelimport.TablibCSVImportParser(CitationImporter)
        headers, rows = parser.parse(sample_csv_4)

        importer = djangomodelimport.ModelImporter(CitationImporter)
        importresult = importer.process(headers, rows, commit=True)

        # Make sure there's no errors
        errors = importresult.get_errors()
        self.assertEqual(errors, [])

        # Check it worked
        c1.refresh_from_db()
        c1_expected = {
            "xxx": "qqqq",
            "yyy": "www",
            "doi": "valid_doi1",
            "isbn": "hello",
        }
        self.assertDictEqual(c1.metadata, c1_expected)

        c2.refresh_from_db()
        c2_expected = {
            "xxx": "aaa",
            "yyy": "bbb",
            "doi": "valid_doi2",
            "isbn": "mate",
        }
        self.assertDictEqual(c2.metadata, c2_expected)
