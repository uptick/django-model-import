from djangomodelimport import ModelImporter, ModelImportForm


def runimporter(request):
    with default_storage.open('books.csv', 'rb') as fh:
        data = fh.read().decode("utf-8")

    importer = ModelImporter(BookImporter)
    preview = importer.process(data, commit=False)
    errors = preview.get_errors()

    if errors:
        print(errors)

    results = importer.process(data, commit=True)
    for result in results:
        print(result.instance)
