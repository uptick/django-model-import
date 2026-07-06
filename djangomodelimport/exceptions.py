class DjangoModelImportException(Exception):
    pass


class InvalidFormException(DjangoModelImportException):
    pass


class InvalidWidgetException(DjangoModelImportException):
    pass
