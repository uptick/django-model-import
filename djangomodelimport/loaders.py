class ImportCache(dict):
    """ A simple cache object keyed by the field name, containing a number of
    cached instance loaders or preloaded caches.
    """
    pass


class CachedInstanceLoader(dict):
    """ A clever cache that queries the database for any missing objects. """
    def __init__(self, queryset, to_field, *args, **kwargs):
        self.queryset = queryset
        self.model = self.queryset.model
        self.to_field = to_field

    def __missing__(self, value):
        try:
            self[value] = inst = self.queryset.get(**{self.to_field: value})
        except self.model.DoesNotExist:
            self[value] = inst = None
        return inst
