
from dataclasses import dataclass
import mmap
import os
from pathlib import Path
import json

import jsons
from PIL import Image, ImagePalette

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
        self.filepath = filepath

        # CREATE A CUSTOM JSON SERIALIZER.
        # Client code can add additional serialization properties as desired,
        # and these can take effect per file.
        self.json_serializer = jsons.fork()

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
    ## \return The subdirectory named after this file created in the provided root.
    def create_export_directory(self, root_directory_path: str) -> str:
        directory_path = os.path.join(root_directory_path, self.filename)
        Path(directory_path).mkdir(parents = True, exist_ok = True)
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

    ## All objects accessible from a file in this application are dumped to JSON,
    ## except the following, which are replaced with placeholders.
    ##  - PIL objects (images and palettes).
    ##    These objects contain a lot of internal information that isn't useful to
    ##    outside observers.
    ##  - Binary streams (including mmap objects).
    ##  - Any byte arrays are dumped to a JSON hexdump format if they are shorter
    ##    than a maximum length. Otherwise, they are replaced with a placeholder.
    def export_metadata(self, root_directory_path, strip_privates = True, maximum_hexdump_length = 0x6f, hexdump_row_length = 0x10):
        # ENABLE SERIALIZING BYTE ARRAYS TO JSON.
        # Because Python only supports one-line lambdas, we first define a standalone function
        # that creates a hexadecimal dump of a byte array to a dictionary, 
        # where each key is the hexadecimal starting address of a row of a custom length
        # and each value is each in that row byte in two-digit hexadecimal notation.
        def hex_dump_dictionary(bytes: bytes, maximum_hexdump_length = 0x6f, hexdump_row_length = 0x10):
            # CHECK THE LENGTH.
            # To avoid clogging the exported JSON with super-long binary dumps,
            # a dump will only be created if the total length of this byte array
            # is less than a specified maximum. If the amount is over this maximum,
            # a placeholder is returned instead of the hexdump.
            total_length = len(bytes)
            if total_length > maximum_hexdump_length:
                return '<blob>'

            # CREATE THE HEXDUMP.
            # The hexsump is stored as a dictionary with entries like the following:
            # <starting_offset>: <byte> <byte> <byte> ... <byte> [up to the maximum row length]
            hex_dump = {}
            for index in range(0, total_length, hexdump_row_length):
                # RECORD THE STARTING OFFSET.
                # This is the location of the first byte in this line.
                # Because JSON does not permit hexadecimal constants as integers,
                # each line's starting offset is in a string.
                starting_offset: str = f'0x{index:02x}'

                # GET THE BYTES FOR THIS ROW.
                raw_row_bytes = bytes[index:index + hexdump_row_length]
                hex_row_bytes = [f'{byte:02x}' for byte in raw_row_bytes]
                # Each byte is separated by a single space.
                row_string = ' '.join(hex_row_bytes)
                hex_dump[starting_offset] = row_string

            # RETURN THE HEXDUMP DICTIONARY.
            return hex_dump

        # CONFIGURE THE JSON SERIALIZER.
        jsons.set_serializer(lambda bytes, **_: hex_dump_dictionary(bytes), bytes, fork_inst = self.json_serializer)
        jsons.set_serializer(lambda bytearray, **_: hex_dump_dictionary(bytearray), bytearray, fork_inst = self.json_serializer)
        jsons.set_serializer(lambda i, **_: '<image>', Image.Image, fork_inst = self.json_serializer)
        jsons.set_serializer(lambda i, **_: '<palette>', ImagePalette.ImagePalette, fork_inst = self.json_serializer)
        jsons.set_serializer(lambda i, **_: '<mmap>', mmap.mmap, fork_inst = self.json_serializer)
        # TODO: Document why this is necessary.
        jsons.suppress_warnings(True, fork_inst = self.json_serializer)

        # EXPORT THE METADATA.
        export_directory = self.create_export_directory(root_directory_path)
        json_filepath = os.path.join(export_directory, f"{self.filename}.json")
        with open(json_filepath, 'w') as json_file:
            # TODO: Add these performance enhancements to speed up the serialization.
            # From https://jsons.readthedocs.io/en/latest/faq.html:
            #  With large data sets, it may take some time for jsons to dump or load. 
            #  This is caused by several checks and scans that jsons does. You can 
            #  increase the speed significantly by using “strict mode”:
            #   jsons.dump(some_obj, strict=True). 
            #  Also make sure to provide type hints for your classes’ attributes. 
            #  This will allow jsons to scan your class only once and use that to get
            #  the attributes of every object of that class it encounters.
            #
            # On top of that, you could see if parallelization gains you anything: 
            #   jsons.dump(some_obj, strict=True, tasks=4). 
            # By default a Process is spawned per task, 
            # but you can also choose to use Thread by providing task_type=Thread.
            file_as_dictionary = jsons.dump(self, strip_privates = strip_privates, fork_inst = self.json_serializer)
            json.dump(file_as_dictionary, json_file, indent = 4)