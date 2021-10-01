import datetime
from testapp.importers import BookImporter, BookImporterWithCache, CitationImporter, CompanyImporter
from testapp.models import Author, Book, Citation, Company, Contact

from django.test import TestCase

from djangomodelimport import DateTimeParserField, ModelImporter, TablibCSVImportParser

sample_csv_1_books = """id,name,author
,How to be awesome,Aidan Lister
,How not to be awesome,Bill
"""

sample_csv_2_books = """id,name,author
111,Howdy,Author Joe
333,Goody,Author Bill
"""

sample_csv_3_citations = """id,author,name,metadata_isbn,metadata_doi
,Fred Johnson,Starburst,ISBN333,doi:111
,Fred Johnson,Gattica,ISBN666,doi:222
"""

sample_csv_4_citations = """id,author,name,metadata_xxx,metadata_yyy,metadata_doi
10,Fred Johnson,Starburst,qqqq,www,valid_doi1
20,Fred Johnson,Gattica,aaa,bbb,valid_doi2
"""

sample_csv_5_books = """id,name,author
,How to be awesome,Aidan Lister
,How to be really awesome,Aidan Lister
,How to be the best,Aidan Lister
,How to be great,Aidan Lister
,How to be so good,Aidan Lister
,How to be better than that,Aidan Lister
,How not to be awesome,Bill
"""

sample_csv_6_companies = """id,name,contact_name,email,mobile,address
,Microsoft,Aidan,aidan@ms.com,0432 000 000,SomeAdress
"""

sample_csv_8_books = """id,name
801,How to be fine
802,How to be average
803,How to be the best
804,How to be awesome
"""

sample_csv_9_books = """id,name,author,skip
,How to be fine,Aidan Lister,true
,How to be average,Aidan Lister,
,How to be the best,Aidan Lister,
,How to be awesome,Aidan Lister,true
"""


class ImporterTests(TestCase):
    def setUp(self):
        pass

    def test_importer(self):
        Author.objects.create(name='Aidan Lister')
        Author.objects.create(name='Bill')

        parser = TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_1_books)

        importer = ModelImporter(BookImporter)
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
        parser = TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_1_books)

        importer = ModelImporter(BookImporter)
        preview = importer.process(headers, rows, allow_insert=False, commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0], (1, [('id', ['Creating new rows is not permitted'])]))

    def test_importer_no_update(self):
        a1 = Author.objects.create(name='Aidan Lister')
        a2 = Author.objects.create(name='Bill')

        Book.objects.create(id=111, name='Hello', author=a1)
        Book.objects.create(id=333, name='Goodbye', author=a2)

        parser = TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_2_books)

        importer = ModelImporter(BookImporter)
        preview = importer.process(headers, rows, allow_update=False, limit_to_queryset=Book.objects.all(), commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0], (1, [('id', ['Updating existing rows is not permitted'])]))

    def test_importer_limited_queryset(self):
        a1 = Author.objects.create(name='Author Joe')
        a2 = Author.objects.create(name='Author Bill')

        b1 = Book.objects.create(id=111, name='Hello', author=a1)
        Book.objects.create(id=333, name='Goodbye', author=a2)

        parser = TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_2_books)

        importer = ModelImporter(BookImporter)
        preview = importer.process(headers, rows, allow_update=True, limit_to_queryset=Book.objects.filter(id=b1.id), commit=False)

        # Make sure there's no errors
        errors = preview.get_errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0], (2, [('id', ['Book 333 cannot be updated.'])]))

    def test_required_fields_on_update(self):
        a1 = Author.objects.create(name='Aidan Lister')
        a2 = Author.objects.create(name='Maddi T')

        b1 = Book.objects.create(id=801, name='Hello b1', author=a1)
        Book.objects.create(id=802, name='Hello b2', author=a1)
        Book.objects.create(id=803, name='Hello b3', author=a2)
        b4 = Book.objects.create(id=804, name='Hello b4', author=a2)

        parser = TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_8_books)

        importer = ModelImporter(BookImporter)
        res = importer.process(headers, rows, allow_update=True, commit=True)

        # Make sure there's no errors
        errors = res.get_errors()
        self.assertEqual(len(errors), 0)

        # Check we updated properly
        b1.refresh_from_db()
        b4.refresh_from_db()
        self.assertEqual(b1.name, 'How to be fine')
        self.assertEqual(b1.author.name, 'Aidan Lister')
        self.assertEqual(b4.name, 'How to be awesome')
        self.assertEqual(b4.author.name, 'Maddi T')

    def test_skip_function(self):
        Author.objects.create(name='Aidan Lister')
        parser = TablibCSVImportParser(BookImporter)
        headers, rows = parser.parse(sample_csv_9_books)

        importer = ModelImporter(BookImporter)
        res = importer.process(headers, rows, allow_update=True, commit=True, skip_func=lambda row: row.get('skip') == 'true')

        # Make sure there's no errors
        errors = res.get_errors()
        self.assertEqual(len(errors), 0)

        # Check two rows were skipped and two imported
        self.assertEqual(res.skipped, 2)
        self.assertEqual(res.created, 2)


class CachedChoiceFieldTests(TestCase):
    def setUp(self):
        pass

    def test_import(self):
        Author.objects.create(name='Aidan Lister')
        Author.objects.create(name='Bill')

        parser = TablibCSVImportParser(BookImporterWithCache)
        headers, rows = parser.parse(sample_csv_5_books)

        importer = ModelImporter(BookImporterWithCache)

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


class JSONFieldTests(TestCase):
    def setUp(self):
        pass

    def test_import(self):
        Author.objects.get_or_create(name="Fred Johnson")

        parser = TablibCSVImportParser(CitationImporter)
        headers, rows = parser.parse(sample_csv_3_citations)

        importer = ModelImporter(CitationImporter)
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
        parser = TablibCSVImportParser(CitationImporter)
        headers, rows = parser.parse(sample_csv_4_citations)

        importer = ModelImporter(CitationImporter)
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


class FlatRelatedFieldTests(TestCase):
    def setUp(self):
        pass

    def test_import(self):
        parser = TablibCSVImportParser(CompanyImporter)
        headers, rows = parser.parse(sample_csv_6_companies)

        importer = ModelImporter(CompanyImporter)
        importresult = importer.process(headers, rows, commit=True)

        # Make sure there's no errors
        errors = importresult.get_errors()
        self.assertEqual(errors, [])

        org = Company.objects.all().first()
        self.assertEqual(org.name, 'Microsoft')
        self.assertEqual(org.primary_contact.name, 'Aidan')

    def test_update(self):
        contact = Contact.objects.create(name='Tapir', email='ziggur@t.com', mobile='5317707')
        company = Company.objects.create(name='Okapi', primary_contact=contact)

        headers = ['id', 'contact_name', 'email']
        rows = [
            {'id': company.id, 'contact_name': 'Foo Fighter Client', 'email': 'b@rrow.com'},
        ]

        importer = ModelImporter(CompanyImporter)
        importresult = importer.process(headers, rows, commit=True)

        # Make sure there's no errors
        errors = importresult.get_errors()
        self.assertEqual(errors, [])

        company.refresh_from_db()
        self.assertEqual(company.primary_contact.name, 'Foo Fighter Client')
        self.assertEqual(company.primary_contact.email, 'b@rrow.com')
        self.assertEqual(company.primary_contact.mobile, '5317707')  # This one should've stayed the same.


class DateTimeParserFieldTests(TestCase):
    def setUp(self):
        self.ledtf = DateTimeParserField()  # Little-endian
        self.medtf = DateTimeParserField(middle_endian=True)

    def test_little_endian_parsing(self):
        self.assertEqual(self.ledtf.to_python('01/02/03'), datetime.datetime(2003, 2, 1, 0, 0))
        self.assertEqual(self.ledtf.to_python('01/02/2003'), datetime.datetime(2003, 2, 1, 0, 0))

    def test_middle_endian_parsing(self):
        self.assertEqual(self.medtf.to_python('01/02/03'), datetime.datetime(2003, 1, 2, 0, 0))
        self.assertEqual(self.medtf.to_python('01/02/2003'), datetime.datetime(2003, 1, 2, 0, 0))

    def test_big_endian_parsing(self):
        self.assertEqual(self.ledtf.to_python('2001/02/03'), datetime.datetime(2001, 2, 3, 0, 0))
        self.assertEqual(self.medtf.to_python('2001/02/03'), datetime.datetime(2001, 2, 3, 0, 0))

        self.assertEqual(self.ledtf.to_python('2018-02-12 17:06:46'), datetime.datetime(2018, 2, 12, 17, 6, 46))
        self.assertEqual(self.medtf.to_python('2018-02-12 17:06:46'), datetime.datetime(2018, 2, 12, 17, 6, 46))
