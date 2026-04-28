"""
Initial setup of the database.

Copyright (c) 2025 Stephanie Johnson
"""

import os, sys, subprocess
import logging
import yaml

from dbcommons.utils import DEFAULT_LOGGING_FORMAT

logger = logging.getLogger(__name__)


def init_db(
        pw: str,
        path_to_config: str
    ) -> None:
    """
    One-time setup for initializing the database.
    This will error out if already created.

    Parameters
    ----------
    pw : str
        Admin account pw for db

    Returns
    -------
    None

    """

    with open(path_to_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        owner = config["db"]["admin_name"]

    path_to_initscript = os.path.join(os.getcwd(),"src","fintrackr","Init_New_db.sh")  
    logger.debug(f"Attempting to run init script at {path_to_initscript}")

    subprocess.run(["chmod", "+x", path_to_initscript])

    exit_code = subprocess.run([path_to_initscript, db_name, owner, pw])
    logger.debug(f"Init script ran with exit code: {exit_code.returncode}, \
                 stdout: {exit_code.stdout}, \
                    stderr: {exit_code.stderr}")

    #TODO capture error(s) from bash script - eg if db already exists so createdb errors
    assert exit_code.returncode == 0, "Failed to execute script to create db"

    logger.info(f"Script to create database named {db_name} executed successfully")


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 3:
        raise TypeError("init_db.py takes exactly two input args (db owner pw to set and path to configuration file)")

    init_db(pw=sys.argv[1],path_to_config=sys.argv[2])