# django-model-import

[![PyPI version](https://badge.fury.io/py/django-model-import.svg)](https://badge.fury.io/py/django-model-import)

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

```bash
poetry add django-model-import
```


## Quickstart

```python
import djangomodelimport

class BookImporter(djangomodelimport.ImporterModelForm):
    name = forms.CharField()
    author = CachedChoiceField(queryset=Author.objects.all(), to_field='name')

    class Meta:
        model = Book
        fields = (
            'name',
            'author',
        )

with default_storage.open('books.csv', 'rb') as fh:
    data = fh.read().decode("utf-8")

# Use tablib
parser = djangomodelimport.TablibCSVImportParser(BookImporter)
headers, rows = parser.parse(data)

# Process
importer = djangomodelimport.ModelImporter(BookImporter)
preview = importer.process(headers, rows, commit=False)
errors = preview.get_errors()

if errors:
    print(errors)

importresult = importer.process(headers, rows, commit=True)
for result in importresult.get_results():
    print(result.instance)
```


## Composite key lookups

Often a relationship cannot be referenced via a single unique string. For this we can use
a `CachedChoiceField` with a `CompositeLookupWidget`. The widget looks for the values
under the `type` and `variant` columns in the source CSV, and does a unique lookup
with the field names specified in `to_field`, e.g. `queryset.get(type__name=type, name=variant)`.

The results of each `get` are cached internally for the remainder of the import minimising
any database access.

```python
class AssetImporter(ImporterModelForm):
    site = djangomodelimport.CachedChoiceField(queryset=Site.objects.active(), to_field='ref')
    type = djangomodelimport.CachedChoiceField(queryset=AssetType.objects.filter(is_active=True), to_field='name')
    type_variant = djangomodelimport.CachedChoiceField(
        queryset=InspectionItemTypeVariant.objects.filter(is_active=True),
        required=False,
        widget=djangomodelimport.CompositeLookupWidget(source=('type', 'variant')),
        to_field=('type__name', 'name'),
    )
    contractor = djangomodelimport.CachedChoiceField(queryset=Contractor.objects.active(), to_field='name')
```


## Flat related fields

Often you'll have a OneToOneField or just a ForeignKey to another model, but you want to be able to
create/update that other model via this one. You can flatten all of the related model's fields onto
this importer using `FlatRelatedField`.

```python
class ClientImporter(ImporterModelForm):
    primary_contact = FlatRelatedField(
        queryset=ContactDetails.objects.all(),
        fields={
            'contact_name': {'to_field': 'name', 'required': True},
            'email': {'to_field': 'email'},
            'email_cc': {'to_field': 'email_cc'},
            'mobile': {'to_field': 'mobile'},
            'phone_bh': {'to_field': 'phone_bh'},
            'phone_ah': {'to_field': 'phone_ah'},
            'fax': {'to_field': 'fax'},
        },
    )

    class Meta:
        model = Client
        fields = (
            'name',
            'ref',
            'is_active',
            'account',

            'primary_contact',
        )
```

## Tests
Run tests with `python example/manage.py test testapp`
