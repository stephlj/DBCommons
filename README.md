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

## TODO

Testing utils assumes "tests/fixtures" structure which is not what FinTrackr has - change

`SQL_to_EDL.py` has several bugs with current Fintrackr schema.

Add testing coverage - cram?