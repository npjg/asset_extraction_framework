import os
from typing import List
import re

## Represents an application whose assets we wish to export.
## An application contains a collection of files, which each
## contain a collection of assets.
##
## Client scripts might use the followng conventions, but the framework
## does not enforce this:
##  - A single list to store the files or assets in the whole application.
##  - Asset export method(s):
##     export_assets
##     export_metadata
##    A single export method might also be desired.
class Application:
    def __init__(self, application_name: str):
        self.application_name = application_name

    ## Finds all files in given search path(s) that match a given regex.
    ## Parses the files matching the detection entries for this application.
    ## The files are guaranteed to be parsed in the order the file detection entries
    ## are provided.
    ## \param[in]  paths - The paths to be searched for matching files.
    ##             Recurses into directories to find matching files.
    ## \param[in] file_detection_entries - Criteria for finding files and parsing them.
    def find_matching_files(self, paths: List[str], regex: str, case_sensitive: bool):
        case_sensitive_search_flag = re.IGNORECASE if not case_sensitive else 0
        matching_filepaths = []
        for path in paths:
            # CHECK IF THE PATH IS A DIRECTORY.
            # If so, descend into the directory to process each file.
            # TODO: Will this recurse forever? Is that a good thing?
            path_is_directory = os.path.isdir(path)
            if path_is_directory:
                # Filename sorting order cannot be relied upon and is an artifact of the filesystem.
                # This option brings some sanity to that.
                directory_listing = os.listdir(path)
                for filename in directory_listing:
                    # PROCESS ANY FILES IN THE SUB-DIRECTORY.
                    # Because the listdir function only returns the filename,
                    # it must be joined with the parent directory path.
                    sub_directory_path = [os.path.join(path, filename)]
                    recursively_matched_filepaths = self.find_matching_files(sub_directory_path, regex, case_sensitive)
                    matching_filepaths.extend(recursively_matched_filepaths)

            # PARSE THE FILE.
            filename: str = os.path.basename(path)
            file_detection_entry_matches = re.match(regex, filename, flags = case_sensitive_search_flag)
            if file_detection_entry_matches:
                # PROCESS THE FILE.
                if os.path.isfile(path):
                    print(f'INFO: Matched file {path} ({regex})')
                    # TODO: Check for collisions to make sure we don't overwrite an existign path.
                    matching_filepaths.append(path)
                # No file should be processed more than once.
                break
        return matching_filepaths
