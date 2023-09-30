
# Each application contains files, which hold multiple assets.
# The application itself does not hold any assets; only global data.

from enum import Enum
import json
import jsons
import os
from typing import List, Union
from .File import File
import re
import logging
from PIL import Image
from PIL import ImagePalette
import mmap

## Uses regular expressions to link the filenames of application files,
## as defined by regular expressions, to file parser classes in this application.
class FileDetectionEntry:
    def __init__(self, filename_regex: str, case_sensitive: bool, file_processor):
        self.filename_regex = filename_regex
        self.case_sensitive = case_sensitive
        self.file_processor = file_processor

## Represents an application whose assets we wish to export.
## An application contains a collection of files, which each
## contain a collection of assets.
class Application:
    def __init__(self, application_name: str):
        # CREATE A PLACE TO STORE THE FILES.
        self.files: List[File] = []
        self.application_name = application_name

    ## Parses the files matching the detection entries for this application.
    ## The files are guaranteed to be parsed in the order the file detection entries
    ## are provided.
    ## \param[in]  paths - The paths to be searched for matching files.
    ##             Recurses into directories to find matching files.
    ## \param[in] file_detection_entries - Criteria for finding files and parsing them.
    def process(self, paths: List[str], file_detection_entries: List[FileDetectionEntry]):
        for file_detection_entry in file_detection_entries:
            case_sensitive_search_flag = re.IGNORECASE if not file_detection_entry.case_sensitive else 0

            for path in paths:
                # CHECK IF THE PATH IS A DIRECTORY.
                # If so, descend into the directory to process each file.
                # TODO: Will this recurse forever? Is that a good thing?
                path_is_directory = os.path.isdir(path)
                if path_is_directory:
                    for filename in os.listdir(path):
                        # PROCESS ANY FILES IN THE SUB-DIRECTORY.
                        # Because the listdir function only returns the filename,
                        # it must be joined with the parent directory path.
                        sub_directory_path = [os.path.join(path, filename)]
                        # TODO: Document why only the first file detection entry is passed in
                        # to the recursive processor. This is to enforce the correct ordering.
                        self.process(sub_directory_path, [file_detection_entry])

                # PARSE THE FILE.
                filename: str = os.path.basename(path)
                file_detection_entry_matches = re.match(file_detection_entry.filename_regex, filename, flags = case_sensitive_search_flag)
                if file_detection_entry_matches:
                    # PROCESS THE FILE.
                    if os.path.isfile(path):
                        print(f'Processing matched file {path}')
                        processed_file = file_detection_entry.file_processor(path)
                        self.files.append(processed_file)
                    # No file should be processed more than once.
                    break

    ## Exports all files in the application.
    ## If any assets have an export method, that method is called.
    ## Any byte arrays are dumped to a JSON hexdump format if they are shorter
    ## than a maximum length. Otherwise, they are replaced with a placeholder
    ## like the below.
    ## All objects accessible from a file in this application are dumped to JSON,
    ## except the following, which are replaced with placeholders.
    ##  - PIL objects (images and palettes).
    ##    These objects contain a lot of internal information that isn't useful to
    ##    outside observers.
    ##  - Binary streams (including mmap objects).
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function, so asset exporters can read any 
    ##            necessary formatting options.
    ## \param[in] 
    def export(self, command_line_arguments, maximum_hexdump_length = 0x6f, hexdump_row_length = 0x10):
        # ENABLE SERIALIZING BYTE ARRAYS TO JSON.
        # Because Python only supports one-line lambdas, we first define a standalone function
        # that creates a hexadecimal dump of a byte array to a dictionary, 
        # where each key is the hexadecimal starting address of a row of a custom length
        # and each value is each in that row byte in two-digit hexadecimal notation.
        def hex_dump_dictionary(bytes: bytes):
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
        # Any byte arrays should be serialized by the preceding function.
        jsons.set_serializer(lambda bytes, **_: '<bytes>', bytes) # ex_dump_dictionary(bytes)
        jsons.set_serializer(lambda i, **_: '<image>', Image.Image)
        jsons.set_serializer(lambda i, **_: '<palette>', ImagePalette.ImagePalette)
        jsons.set_serializer(lambda i, **_: '<mmap>', mmap.mmap)
        # TODO: DOcument why this is necessary.
        jsons.suppress_warnings(True)

        # EXPORT THE ASSETS IN THE APPLICATION.
        # First, we want to create a directory to hold all the exported files
        # from this application.
        application_export_subdirectory: str = os.path.join(command_line_arguments.export, self.application_name)
        for index, file in enumerate(self.files):
            # EXPORT THE FILE.
            # This method creates a directory for the file.
            print(f'Exporting assets in {file.filepath}')
            file.export(application_export_subdirectory, command_line_arguments)

        # EXPORT THE JSON FOR THE APPLICATION.
        print(f'Exporting JSON for whole application')
        json_export_filename = f'{self.application_name}.json'
        json_export_filepath = os.path.join(application_export_subdirectory, json_export_filename)
        with open(json_export_filepath, 'w') as json_file:
            asset_tree = jsons.dump(self.files, strip_privates = True)
            json.dump(asset_tree, json_file, indent = 2)
