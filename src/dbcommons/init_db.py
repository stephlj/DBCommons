"""
Initial setup of the database.

Copyright (c) 2025 Stephanie Johnson
"""

import os, sys, subprocess
import logging
import yaml
import importlib.resources as pkg_resources

from dbcommons.utils import DEFAULT_LOGGING_FORMAT

logger = logging.getLogger(__name__)


def init_db(
        pw: str,
        path_to_config: str,
        path_to_schema: str
    ) -> None:
    """
    One-time setup for initializing the database.
    This will error out if already created.

    Parameters
    ----------
    pw : str
        Admin account pw for db
    path_to_config : str
        relative path to config file with db name, owner name
    path_to_schema : str
        relative path to schema file for db

    Returns
    -------
    None

    """

    with open(path_to_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        owner = config["db"]["admin_name"]

    with pkg_resources.as_file(
        pkg_resources.files("dbcommons").joinpath("Init_New_db.sh")
    ) as script_path:
        subprocess.run(["chmod", "+x", str(script_path)])
        # check=True means execution will halt if there's a non-zero exit code
        subprocess.run([str(script_path), db_name, owner, pw, path_to_schema], check=True)


    logger.info(f"Script to create database named {db_name} executed successfully")


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 3:
        raise TypeError("init_db.py takes exactly three input args (db owner pw to set, path to configuration file, path to schema file)")

    init_db(pw=sys.argv[1],path_to_config=sys.argv[2], path_to_schema=sys.argv[3])