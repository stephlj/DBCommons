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

### Load data

The utilities provided here are heavily geared towards applications that load data from csvs.

Recommended: Use `csv_to_dataclass` in `dataclass_utils.py` to first load from a csv into a pre-defined
dataclass that represents in the python layer the way data are stored in the db layer. Then, use
`insert_many_w_class` to load into the db (ideally via a temporary staging table, if you want to perform checks
like not loading duplicates before inserting from the staging table into a permanent db table. The DBConn class
has utilities for creating and dropping staging tables).

Or, use `insert_many_w_class` to insert directly from a dataclass in memory (from a csv originally or otherwise).

DBCommons also allows loading directly from a csv into a staging table in the db, using the `csv_to_staging`
method in the `DBConn` class. This direct loading method is not recommended, however; loading a csv
into a pre-defined dataclass first allows for better input handling (making sure db columns match
input data, etc).

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

- Testing utils assumes "tests/fixtures" structure which is not what FinTrackr has - change (probably in FinTrackr)
- `SQL_to_EDL.py` has several bugs with current Fintrackr schema.
- Add testing coverage - cram? for CLIs
- Extend support for nested dataclasses in `execute_query_w_class`. Plan suggested by Claude:
`execute_query_w_class` uses psycopg's `class_row(return_class)`, which calls `return_class(**row)` with the query's flat column names. For `NestedFruit` (an example in the testing suite), that means `NestedFruit(fruit=..., nums=..., mama_bear=..., ...)`, which raises `TypeError` for the unexpected keyword `mama_bear`. Nothing turns the flat row back into a nested object.

`_from_flat_row` builds nested objects, but it always runs `csv_parser` on each value. Values from the database already have the right Python types, so that step needs to be optional:

```
def _from_flat_row(cls: Type[T], row: dict, parse: bool) -> T:
    kwargs = {}
    for f, field_type in _fields_and_types(cls):
        if _is_nested_dataclass(field_type):
            kwargs[f.name] = _from_flat_row(field_type, row, parse)
        elif parse:
            kwargs[f.name] = f.metadata['csv_parser'](row[f.name])
        else:
            kwargs[f.name] = row[f.name]
    return cls(**kwargs)

def flat_dict_to_dataclass(cls: Type[T], row: dict) -> T:
    """Inverse of dataclass_to_flat_dict: rebuild a (possibly nested) `cls` from a flat dict."""
    return _from_flat_row(cls, row, parse=False)
```
`csv_to_dataclass` would call `_from_flat_row(cls, r, parse=True)`. 

In `db_conn.py`, swap `class_row` for psycopg's `kwargs_row`:

```
from psycopg.rows import dict_row, kwargs_row
...
with self._conn.cursor(row_factory=kwargs_row(lambda **row: flat_dict_to_dataclass(return_class, row))) as curs:
```
The docstring's advice (`sql.Identifier(f.name) for f in fields(cls)`) also stops working once the class is nested. It should become `[sql.Identifier(n) for n, _ in flat_col_defs(cls)]`, and testing coverage added for `execute_query_w_class` with nested returning class should build its query that way.

`flat_dict_to_dataclass` also gives you a cheap round-trip unit test: `flat_dict_to_dataclass(type(x), dataclass_to_flat_dict(x)) == x`. With it, you could later replace the hand-built `FoodProps(...)` in ForkWise's `calc_recipe_totals_per_serving`.
```