# add_user.py
#
# Copyright (c) 2025 Stephanie Johnson

import sys
import logging
import psycopg
import yaml

from dbcommons.utils import DEFAULT_LOGGING_FORMAT

logger = logging.getLogger(__name__)

def add_user(
        name: str,
        pw: str,
        admin_pw: str,
        path_to_config: str
) -> None:
    """Add a new user.

    Parameters
    ----------
    name :  str
        User name to add. Usernames will be associated with any data they add to the db.
    pw : str
        Password for new user.
    admin_pw : str 
        The password for the db owner, set when init_db was run.
    path_to_config : str
        Path to the config file to use, to get db_name, db_admin.

    Returns
    -------
    None

    TODO later: add separate dev role if users can't write to all tables
    """

    with open(path_to_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        db_admin = config["db"]["admin_name"]

    # Connect to the db as admin who has permissions to create role
    conn = psycopg.connect(f"dbname={db_name} user={db_admin} password={admin_pw} host='localhost'")
    conn.autocommit = True
    cur = conn.cursor()
    
    # TODO add to an existing user role
    cur.execute(f"CREATE ROLE {name} WITH LOGIN PASSWORD '{pw}' NOCREATEDB NOCREATEROLE")
    cur.execute(f"GRANT CONNECT ON DATABASE {db_name} TO {name}")
    cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {name}") # So users can create staging tables
    cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {name}")
    cur.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO {name}")
    cur.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {name}") # this is so I can get fetchalls from RETURNING clauses, I think
    # Changed to using cur.copy_expert, so this line shouldn't be necessary anymore:
    # cur.execute(f"GRANT pg_read_server_files TO {name}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)
    if len(sys.argv) != 5:
        raise TypeError("add_user.py accepts exactly 4 args")
    
    add_user(name=sys.argv[1], pw=sys.argv[2], admin_pw=sys.argv[3],path_to_config=sys.argv[4])