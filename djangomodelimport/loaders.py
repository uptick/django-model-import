class CachedInstanceLoader(dict):
    """ A clever cache that queries the database for any missing objects. """
    def __init__(self, queryset, to_field, *args, **kwargs):
        self.queryset = queryset
        self.model = self.queryset.model
        self.to_field = to_field
        self.multifield = isinstance(to_field, list) or isinstance(to_field, tuple)

    def __missing__(self, value):
        if self.multifield:
            params = dict(zip(self.to_field, value))
        else:
            params = {self.to_field: value}

        try:
            self[value] = inst = self.queryset.get(**params)
        except self.model.DoesNotExist:
            self[value] = inst = None
        except self.model.MultipleObjectsReturned:
            self[value] = inst = None
        return inst
