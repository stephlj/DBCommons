"""
Extracting some commonly used code for testing (manual and automated).

Copyright (c) 2026 Stephanie Johnson
"""

import os, subprocess
import yaml

from dbcommons.init_db import init_db
from dbcommons.add_user import add_user
import dbcommons.db_conn

TEST_CONFIG_PATH = os.path.join(os.getcwd(),"tests","data","test_config.yml")
TEST_DATA_PATH = os.path.join(os.getcwd(),"tests","data")

def config_params() -> dict:
    with open(TEST_CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        test_db_name = config["db"]["db_name"]
        test_owner = config["db"]["admin_name"]

    return {
        "test_db_name" : test_db_name,
        "test_owner": test_owner,
        "owner_pw": "test_pw",
        "user": "test_user",
        "user_pw" :"pw"
    }

def set_up_test_DB(params: dict) -> None:
    """
    Parameters
    ----------
    params : dict
        Output of config_params
    """

    init_db(pw=params["owner_pw"], path_to_config=TEST_CONFIG_PATH)

    add_user(name=params["user"], 
                pw=params["user_pw"], 
                admin_pw = params["owner_pw"], 
                path_to_config=TEST_CONFIG_PATH
    )

    db_conn = dbcommons.db_conn.DBConn(user=params["user"], pw=params["user_pw"], db_name=params["test_db_name"])

    return db_conn

def tear_down_test_DB(db_conn: object, params: dict) -> None:
    """
    Parameters
    ----------
    db_conn: DBConn object

    params: dict
        Result of loading a config file; specifies db name to tear down, etc
    """
    db_conn.close()

    # Delete testing db
    exit_code = subprocess.run(["dropdb", params["test_db_name"]])
    exit_code2 = subprocess.run(["dropuser",params["user"]])
    exit_code3 = subprocess.run(["dropuser",params["test_owner"]])

    # We put these at the end to ensure teardown completes even if one of these fails.
    # Note that the @classmethod decorator changes the first arg to the class not
    # an instance of the class, so self.assertEqual fails.
    assert exit_code.returncode==0, "Failed to remove testing db, must now remove manually"
    assert exit_code2.returncode==0, "Failed to remove testing user, must now remove manually"
    assert exit_code3.returncode==0, "Failed to remove testing db owner, must now remove manually"