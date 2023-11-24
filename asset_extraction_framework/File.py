
from dataclasses import dataclass
import mmap
import os
from pathlib import Path

from .Asserts import assert_equal

## Models a file (whether actually on the filesystem, or logically from an in-memory archive)
## that holds one or more assets.
class File:
    ## \param[in] - filepath: The filepath of the file, if it exists on the filesystem.
    ##                        Defaults to None if not provided.
    ## \param[in] - stream: A BytesIO-like object that holds the file data, if the file does
    ##                      not exist on the filesystem.
    ## NOTE: It is an error to provide both a filepath and a stream, as the source of the data
    ##       is then ambiguous.
    def __init__(self, filepath: str = None, stream = None):
        # CREATE A PLACE TO HOLD THE ASSETS IN THIS FILE.
        self.assets = []

        # SET THE FILEPATH FOR THIS FILE.
        self.filepath = filepath

        # MAP THE FILE DATA.
        # A filepath can be provided to open a file from disk, or an in-memory binary stream can be provided.
        # However, providing both of these is an error.
        # First, we see if the data sources are ambiguous.
        more_than_one_data_source_provided: bool = filepath is not None and stream is not None
        if more_than_one_data_source_provided:
            raise ValueError('A filepath and a stream cannot both be provided to define a stream.' 
                             'The data source of the file would be ambiguous')
        only_filepath_provided = filepath is not None
        if only_filepath_provided:
            # MAP THE DATA AT THIS FIELPATH TO A BINARY STREAM WITH READ-ONLY ACCESS.
            with open(filepath, mode = 'rb') as file:
                # By specifying a length of zero, we will map the whole stream.
                self.stream = mmap.mmap(file.fileno(), length = 0, access = mmap.ACCESS_READ)
            self.length = os.path.getsize(filepath)
        only_stream_provided: bool = stream is not None
        if only_stream_provided:
            # USE THE EXISTING STREAM.
            # This is useful for fully in-memory files (like files read from an archive)
            # and never stored on the filesystem.
            self.stream = stream
        self.filepath = filepath

    ## Exports all the assets in this file.
    ## \param[in] root_directory_path - The root directory where the assets should be exported.
    ##            A subdirectory named after this file will be created in the root, 
    ##            and asset exporters may create initial subdirectories.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function, so asset exporters can read any 
    ##            necessary formatting options.
    ## \return The subdirectory named after this file created in the provided root.
    def export(self, root_directory_path: str, command_line_arguments) -> str:
        # CREATE THE DIRECTORY FOR THIS FILE.
        directory_path = os.path.join(root_directory_path, self.filename)
        Path(directory_path).mkdir(parents = True, exist_ok = True)

        # EXPORT THE ASSETS INTO THIS FILE'S DIRECTORY.
        if isinstance(self.assets, dict):
            assets_list = self.assets.values()
        else:
            assets_list = self.assets
        for index, asset in enumerate(assets_list):
            # SET THE ASSET NAME IF IT IS NOT ALREADY SET.
            # This ensures every asset has a unique name within this file.
            if asset.name is None:
                asset.name = f'{index}'

            # EXPORT THE ASSET.
            asset.export(directory_path, command_line_arguments)
        
        # RETURN THE PATH OF THE CREATED DIRECTORY.
        return directory_path

    ## Seeks backward from the current stream position.
    def rewind(self, bytes_to_rewind: int):
        self.stream.seek(self.stream.tell() - bytes_to_rewind)

    ## Returns the base filename of the file modeled by this class.
    @property
    def filename(self) -> str:
        return os.path.basename(self.filepath)

    ## Returns only the extension of the file modeled by this class.
    @property
    def extension(self) -> str:
        # RETURN THE EXTENSION.
        return os.path.splitext(self.filename)[1].lstrip('.')

    ## Verifies the binary stream is at the correct byte position.
    ## \param[in] expected_position - The expected byte position of the binary stream.
    ## \param[in] warn_only - When True, do not raise an exception for a failed assertion; rather, print a warning and return False.
    def assert_at_stream_position(self, expected_position: int, warn_only: bool = False) -> bool:
        return assert_equal(self.stream.tell(),  expected_position, 'stream position', warn_only)
