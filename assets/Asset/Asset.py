
class Asset:
    def __init__(self, name = None):
        # SET THE UNIQUE IDENTIFIER FOR THIS ASSET.
        # In the export, this name will be used as 
        # If the name is None at export time, the ordinal (position) of the asset is used as an ID instead.
        self.name = name

    def export(self, filename: str, *args):
        # DO NOTHING.
        # Because there is no actual data stored in this base class,
        # there is nothing to do.
        pass