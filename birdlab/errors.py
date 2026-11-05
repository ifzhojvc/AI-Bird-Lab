class BirdLabError(Exception):
    pass


class InputError(BirdLabError):
    pass


class ModelError(BirdLabError):
    pass


class StorageError(BirdLabError):
    pass
