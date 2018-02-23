class CachedInstanceLoader(dict):
    """ A clever cache that queries the database for any missing objects.

    If there's an error, it's only raised against the first item that causes it, then it's
    cached for extra speed.
    """
    def __init__(self, queryset, to_field, *args, **kwargs):
        self.queryset = queryset
        self.model = queryset.model
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
            self[value] = inst = None  # Further warnings will be surpressed
            raise
        except self.model.MultipleObjectsReturned:
            self[value] = inst = None  # Further warnings will be surpressed
            raise
        return inst
