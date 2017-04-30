# django-model-import

Django Model Import is a light weight CSV importer built for speed.

It uses a standard Django `ModelForm` to parse each row, giving you a familiar API to work with
for data validation and model instantiation. In most cases, if you already have a `ModelForm`
for the `ContentType` you are importing you do not need to create an import specific form.

To present feedback to the end-user running the import you can easily generate a preview
of the imported data by toggling the `commit` parameter.

It also provides some import optimized fields for ForeignKey's, allowing preloading all
possible values, or caching each lookup as it occurs, or looking up a model where multiple
fields are needed to uniquely identify a resource.


## Installation

Standard pip install:

```bash
pip install django-model-import
```


## Quickstart

```python
from djangomodelimport import ModelImportForm, ModelImporter

class BookImporter(ModelImportForm):
    name = forms.CharField()
    author = CachedChoiceField(queryset=Author.objects.all(), to_field='name')

    class Meta:
        model = Book

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

```
