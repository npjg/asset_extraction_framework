

import json
import jsons

class Exportable:
    def __init__(self):
        self.assets = []

    @property
    def json(self):
        assets_json_dump = []
        for index, asset in enumerate(self.assets):


    # This does not contain any asset-specific export logic.
    # That must be defined per application.
    def export(self, export_directory):
        # VERIFY THE PROVIDED FILEPATH IS VALID.

        # CREATE THE EXPORT DIRECTORY.
        # Can we validate the path first too? That can be done with the command-line arguments.

        # EXPORT THE ASSETS IN THE APPLICATION.
        # Each asset can itself contain assets, and so on.
        # All of these should be exported.
        assets_json_dump = []

            # EXPORT THE ASSETS WITHIN THIS ONE.
