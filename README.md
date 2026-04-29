# DBCommons: Common db setup and connection utilities

Code to initialize a postgres database, add users, and a class to manage connections.

Geared towards databases that load from csvs (like Fintrackr and ForkWise).

## TODO

`db_conn._import_csv` needs to be generalized - have column names as inputs.

Are the testing utils still useful if I subclass DBConn?

`SQL_to_EDL.py` has several bugs with current Fintrackr schema.

Add testing coverage - cram?