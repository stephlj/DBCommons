# DBCommons: Common db setup and connection utilities

Code to initialize a postgres database, add users, and a class to manage connections.

Geared towards databases that load from csvs (like Fintrackr and ForkWise).

## Example usage

### Initialize a new db

(One-time action) Initialize a db with a schema file.

Bash script:

```
db_name='my_db'
owner='owner'
owner_pw='pw'
schema_path='<path_to_sql_file>'
./src/dbcommons/Init_New_DB.sh $db_name $owner $owner_pw $schema_path
```

Or if you have a config file that sets up db name etc, using python script:

```
config_path='<path_to_config.yml>'
schema_path='<path_to_schema.sql>'
python ./src/dbcommons/init_db.py '<owner_pw>' $config_path $schema_path
```

### Add a user
```
python ./src/dbcommons/add_user.py <new user name> <new user password> <db admin password>
```

## Dev

This package uses `uv` for package and virtual environment management, based on the very helpful tutorials at [Sebastia Agramunt Puig's blog](https://agramunt.me/posts/python-virtual-environments-with-uv/).

Create the environment with `uv venv .venv` and then run `uv sync --all-extras` (to get developer extras).

Activate with `source .venv/bin/activate`.

Add dependencies with `uv add <package1> <package2>`. If you get an error that looks like:

```
No solution found when resolving dependencies:
  ╰─▶ Because there are no versions of unittest and your project depends on unittest, we can conclude that your project's requirements are
      unsatisfiable.
```
you already have the package (e.g. it's a package that comes with all python installs). I love `uv` but its error messages can be quite unhelpful.

Use `pytest` to run the tests. (For quick debugging: Add `-s` or `--capture=no` to print print statements to console.)

Quick manual testing/debugging setup using the tools in `testing_utils.py`:

```
from dbcommons.testing_utils import set_up_test_DB, tear_down_test_DB, config_params
from dbcommons.testing_utils import TEST_CONFIG_PATH, TEST_DATA_PATH
from dbcommons.db_conn import DBConn
params = config_params()
utils.set_up_test_DB(params=params)
conn = DBConn(user="test_user", pw="user_pw", db_name="test_db")
```

When done, run:

```
utils.tear_down_test_DB(db_conn = conn, params = params)
```

## TODO

Testing utils assumes "tests/fixtures" structure which is not what FinTrackr has - change

`SQL_to_EDL.py` has several bugs with current Fintrackr schema.

Add testing coverage - cram? for CLIs
Fix bug in DBConn test - what type of error is Errno2?