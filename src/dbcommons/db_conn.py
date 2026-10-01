"""
Class that connects to the database and manages interactions with it.

Copyright (c) 2025, 2026 Stephanie Johnson
"""

import psycopg
import logging

from typing import List, Any, TypeVar, Type
from psycopg import errors as psql_errors
from psycopg.rows import dict_row, class_row
from psycopg import sql

from dbcommons.dataclass_utils import dataclass_to_flat_dict
from dbcommons.utils import check_csv_path

# Assign a type, to be established when a function is called, to variable T.
# This is only used for type hints, but allows us to say: def func(input: T) -> T
# and indicate that the arg and return are both the same type. Using "Any"
# would lose track of that type. Since none of the dataclasses these utilities
# use are defined here, we can't define the type these functions handle
# until runtime.
T = TypeVar("T")

class DBConn:

    def __init__(self, user: str, pw: str, db_name: str):
        self._user = user
        self._pw = pw
        self._db_name = db_name
        self._conn = psycopg.connect(f"dbname={self._db_name} user={self._user} password={self._pw} host='localhost'")
        self._conn.autocommit = True

        self._logger = logging.getLogger(__name__)

    def close(self):
        try:
            self._conn.close()
        except Exception as e:
            self._logger.exception("db_conn object failed to close")
            # Ignore errors during shutdown - TODO this isn't ideal but otherwise the connection hangs ...
            pass
    
    def __del__(self):
        # Fall back safety net to make sure connection is closed when garbage collected
        self.close()

    def __enter__(self):
        # So that DBConn object can be used within a "with" clause
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    def _import_csv(self, col_types: List[str], dest_table: str, path_to_file: str) -> None:
        """
        To avoid granting permission to read server files, I use a client-side copy
        This function wraps that copy command.

        Assumes no header in the csv. Assumes column order in csv is the same as the order in col_types - 
        any checking of this assumption should be handled by the calling function.
        
        Parameters
        ----------
        col_types : List[str]
            List of strings representing col SQL types, in order they appear in the csv to load
            E.g. ["date", "numeric", "text"]
        dest_table: str
            Name of table to copy into (needs to already exist)
        path_to_file: str
            Path to file whose contents are to be copied. Must be a csv.
        
        Returns
        -------
        None. Raises exceptions if unsuccessful.

        """

        # Handle some common possible exceptions up front:
        check_csv_path(path_to_file=path_to_file)

        with self._conn.cursor() as curs: 
            self._logger.debug(f"Importing from file {path_to_file}")
            try:
                with open(path_to_file, "r") as f:
                    with curs.copy(f"COPY {dest_table} FROM STDIN WITH (FORMAT csv, HEADER false)") as copy:
                        copy.set_types(col_types)
                        for line in f:
                            copy.write(line) # TODO figure out the difference between write and write_row
            except Exception as e:
                self._logger.error(f"Failed to import from file {path_to_file} with exception: {e}")
    
    def execute_action(self, query: str, vals: tuple = ()) -> str:
        """
        Convenience function. Execute an action for which I want the response message, not a fetch.

        Calling function should handle expected exceptions via specific
        exception classes. No try-except block here.

        Parameters
        ----------
        query : str
            SQL statement to execute
        vals: tuple
            Values, in order, for any/all %s's in the query string

        Returns
        -------
        str
            conn.cursor.statusmessage

        I could wrap this in a transaction, but that's more opaque if something goes sideways,
        for the non-prod situations I'm using this for.

        For future reference, it would look something like:

        - BEGIN statement or run in ISOLATION_LEVEL_READ_COMMITTED or similar
        try:
            with self._cur ...
        except Exception as e:
            self._conn.rollback()
            raise e
        self._conn.commit()

        """
        # The with statement automatically closes cursor after execution
        with self._conn.cursor() as curs: 
            self._logger.debug(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.statusmessage

        
    def execute_query(self, query: str, vals: tuple = ()) -> List[dict] | None:
        """
        Returns the result of a fetch to the database, after query execution.

        Calling function should handle expected exceptions (like violation of
        unique constraints if duplicates are attempted to be inserted) via specific
        exception classes. No try-except block here.

        Parameters
        ----------
        query : str
            SELECT or INSERT statement to execute
            (something where the return should be the result of a fetchall, rather 
            than a status message)
            Args need to be passed in separately using %s in the query string
            (ie using parameterized SQL)
        vals: tuple
            Values, in order, for all %s's in the query string

        Returns
        -------
        List of dicts, or None
            result of fetchall if the SQL has a RETURNING clause, 
            or None if the query is malformed/table doesn't exist/no RETURNING
            Note to self: RETURNING in SQL returns a table; dict_row turns each row
            into a dict, witih column names as keys

        """

        with self._conn.cursor(row_factory=dict_row) as curs: 
            self._logger.debug(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.fetchall()
        
    def execute_query_w_class(self, query: str, return_class: Type[T], vals: tuple = ()) -> List[T] | None:
        """
        Returns the result of a fetch to the database, after query execution, as a class instance.

        Calling function should handle expected exceptions (like violation of
        unique constraints if duplicates are attempted to be inserted) via specific
        exception classes. No try-except block here.

        Dataclass fields MUST MATCH COLUMN NAMES IN DB EXACTLY. Best way to ensure this is to use 
        sql.SQL(",").join(sql.Identifier(f.name) for f in fields(cls)) in the query. See example
        in test_dbconn.py.

        Nested dataclasses as the return_class are NOT SUPPORTED.

        Parameters
        ----------
        query : str
            SELECT or INSERT statement to execute
            (something where the return should be the result of a fetchall, rather 
            than a status message)
            Args need to be passed in separately using %s in the query string
            (ie using parameterized SQL)
        return_class : Any [dataclass]
            Dataclass that conforms to the data model of the query return.
        vals: tuple
            Values, in order, for all %s's in the query string

        Returns
        -------
        Dataclass, or None
            result of fetchall if the SQL has a RETURNING clause, 
            or None if the query is malformed/table doesn't exist/no RETURNING
            Each row is returned as return_class class

        """

        with self._conn.cursor(row_factory=class_row(return_class)) as curs: 
            self._logger.debug(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.fetchall()
        
    def insert_many_w_class(self, tablename: str, insert_cls: List[Any]) -> int:
        """
        Use cursor.executemany() to insert multiple rows at once. Each row inserted will be an 
        instance of insert_cls.

        Parameters
        ----------
        tablename : str
            Table to insert into
        insert_cls : Any [dataclass]
            Dataclass to insert, one per row. Dataclass field names and types must
            match columns of table to insert into.

        Returns
        -------
        int, number of rows inserted
        """

        with self._conn.cursor() as curs:
            # cols = [f.name for f in fields(insert_cls[0])]
            # vals = [asdict(c) for c in insert_cls] # Breaks with nested dataclasses
            vals = [dataclass_to_flat_dict(c) for c in insert_cls]
            cols = list(vals[0].keys())
            query = sql.SQL("INSERT INTO {name} ({cols}) VALUES ({val_str});").format(name=sql.Identifier(tablename), 
                                                                                    cols=sql.SQL(",").join(map(sql.Identifier, cols)),
                                                                                    val_str=sql.SQL(",").join(map(sql.Placeholder, cols)))                                                                                                              
            self._logger.debug(f"Executing query: {query}, with vals: {vals}")
            curs.executemany(query, vals)
            return curs.rowcount

        
    def execute_scalar(self, query: str, vals: tuple = ()) -> int | str | None:
        """
        Returns the result of a fetch to the database, after query execution.

        Assumes single return (will error if the query returns multiple rows).

        Parameters
        ----------
        query : str
            SELECT or INSERT statement to execute
            (something where the return should be the result of a fetchall, rather 
            than a status message)
            Args need to be passed in separately using %s in the query string
            (ie using parameterized SQL)
        vals: tuple
            Values, in order, for all %s's in the query string

        Returns
        -------
        int | str | None
            Returns None if no rows matched query

        """

        with self._conn.cursor() as curs: 
            self._logger.debug(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            row_tuple = curs.fetchall() # Returns a list of tuples (each row a tuple)
        
        if len(row_tuple)==0:
            return None
        
        if len(row_tuple) != 1:
            log_msg = f"Query: {query} with vals: {vals} did not return a single row as expected"
            self._logger.error(log_msg)
            raise ValueError(log_msg)
        
        if len(row_tuple[0]) != 1:
            log_msg2 = f"Query: {query} with vals: {vals} did not return a single item as expected"
            self._logger.error(log_msg2)
            raise ValueError(log_msg2)
        
        return row_tuple[0][0]
    
    def create_staging(self, col_defs: List[tuple[str]]) -> None:
        """ 
        Create a staging table; error if exists

        Parameters
        ----------
        col_defs : List[tuple[str]]
            Columns of the staging table.
            Each tuple in the list is (col_name, col_type), eg ('posted date', 'date').
            Note types need to be strings not classes (can be obtained by <type>.__name__)

        Returns
        -------
        None
        """

        try:
            rows_before = self.execute_scalar("SELECT COUNT(*) FROM staging;")
            if rows_before >= 0 :
                msg = "Staging table already exists!"
                self._logger.error(msg)
                raise ValueError(msg)
        except psql_errors.UndefinedTable as e:
            self._logger.debug("Table staging does not exist; will create")
        except Exception as e:
            self._logger.error(f"Table staging exists but query of staging table did not execute with exception: {e}")
            raise

        col_and_type = ", ".join(f'{a} {b}' for a, b in col_defs)
        r1 = self.execute_action(f"CREATE TABLE staging ({col_and_type});")
        if r1 != "CREATE TABLE":
            msg = "Failed to create staging table"
            self._logger.error(msg)
            raise ValueError(msg)

    def drop_staging(self) -> None:
        # Drop the staging table
        r = self.execute_action("DROP TABLE staging;")
        if r != "DROP TABLE":
            msg = "Unable to drop staging table"
            self._logger.error(msg)
            raise ValueError(msg)

    
    def csv_to_staging(self, csv_path: str, csv_columns: List[tuple[str]]) -> int:
        """ 
        FinTracker and ForkWise accept csv inputs.
        Load csv from disk into a temporary staging table. 
        Calling function must create and drop the staging table, after loading from
        staging table into the relevant permanent table(s) in the db.

        Parameters
        ----------
        csv_path : str
            path to csv of transactions or balances
        csv_columns : List[tuple[str]]
            Columns in the csv which become columns in the staging table.
            Each tuple in the list is (col_name, col_type), eg ('posted date', 'date').
            Note types need to be strings not classes (can be obtained by <type>.__name__)
            Note also that only col_type is now used by this function; but keeping col_name
            improves interpretability

        Returns
        -------
        int
            Number of rows added to the staging table
        """
        
        try:
            rows_before = self.execute_scalar("SELECT COUNT(*) FROM staging;")
            if rows_before > 0:
                msg = "Staging table already exists with content, cannot proceed with new csv load"
                self._logger.error(msg)
                raise ValueError(msg)
        except psql_errors.UndefinedTable as e:
            self._logger.error("Staging table must already exist before csv load")
            raise

        col_types = [f"{b}" for _, b in csv_columns]
        r2 = self._import_csv(col_types=col_types, dest_table="staging", path_to_file=csv_path)
        if r2==0: # This will happen if copy fails; eg if try to insert too many columns
            self._logger.info("No rows added to staging table")
            return 0

        # Query how many rows are now in staging table
        rows_after = self.execute_scalar("SELECT COUNT(*) FROM staging;")
        self._logger.debug(f"After loading new transactions, staging has {rows_after} rows")

        return rows_after