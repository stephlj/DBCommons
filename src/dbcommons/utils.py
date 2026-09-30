"""
Constants and utilities used by multiple modules.

Copyright (c) 2026 Stephanie Johnson
"""

import os

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

def check_csv_path(path_to_file: str)->None:
    # Helper function used by functions and methods that take csvs as inputs - 
    # handle some common potential errors. No returns; just raises a ValueError
    # if the file doesn't exist or isn't a .csv.

    if not os.path.isfile(path_to_file):
        msg = f"{path_to_file} not a path to a file that exists"
        raise ValueError(msg)
    
    if not os.path.splitext(path_to_file)[1] == ".csv":
        msg = f"{path_to_file} not a csv"
        raise ValueError(msg)