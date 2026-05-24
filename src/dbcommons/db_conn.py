"""
Class that connects to the database and manages interactions with it.

Copyright (c) 2025, 2026 Stephanie Johnson
"""

import psycopg
import logging
import os

from typing import List

class DBConn:

    def __init__(self, user: str, pw: str, db_name: str):
        self.user = user
        self.pw = pw
        self.db_name = db_name
        self._conn = psycopg.connect(f"dbname={self.db_name} user={self.user} password={self.pw} host='localhost'")
        self._conn.autocommit = True

        self._logger = logging.getLogger(__name__)

    def close(self):
        try:
            self._conn.close()
        except Exception as e:
            # Ignore any erros during shutdown
            self._logger.exception("db_conn object failed to close")
            pass
    
    def _import_file(self, dest_table: str, path_to_file: str) -> int:
        """
        To avoid granting permission to read server files, I use a client-side copy
        This function wraps that copy command.

        ASSUMES column type order of (date, amount, description), ie (date, numeric, text) 
        which works for both balances and transactions per my current loading schema.
        
        Parameters
        ----------
        dest_table: str
            Name of table to copy into (should already exist)
        path_to_file: str
            Path to file whose contents are to be copied. Must be a csv.
        
        Returns
        -------
        int:
            1 if successful copy, 0 if an exception occurred

        """
        response = 0 # assume failure :)

        if not os.path.isfile(path_to_file):
            self._logger.error(f"DBConn._import_file: {path_to_file} not a path to a file that exists")
            return response
        if not os.path.splitext(path_to_file)[1] == ".csv":
            self._logger.error(f"DBConn._import_file: {path_to_file} not a csv")
            return response

        with self._conn.cursor() as curs: 
            self._logger.info(f"Importing from file {path_to_file}")
            try:
                with open(path_to_file, "r") as f:
                    with curs.copy(f"COPY {dest_table} FROM STDIN WITH (FORMAT csv, HEADER false)") as copy:
                        copy.set_types(["date", "numeric", "text"]) # TODO should this not be hardcoded, if I'm not hard-coding dest_table?
                        for line in f:
                            copy.write(line) # TODO figure out the difference between write and write_row
                response = 1
            except Exception as e:
                self._logger.error(f"Failed to import from file {path_to_file} with exception: {e}")
            finally:
                return response
    
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
            self._logger.info(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.statusmessage

        
    def execute_query(self, query: str, vals: tuple = ()) -> List[tuple] | None:
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
        List of tuples, or None
            result of fetchall if the SQL has a RETURNING clause, 
            or None if the query is malformed/table doesn't exist/no RETURNING
            Note to self: RETURNING in SQL returns a table; psycopg fetchall
            turns this into a tuple of rows

        """

        with self._conn.cursor() as curs: 
            self._logger.info(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.fetchall() # Returns a list of tuples (each row a tuple)
        
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
            self._logger.info(f"Executing query: {query}, with vals: {vals}")
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
    
    def csv_to_staging(self, csv_path: str, csv_columns: List[tuple[str]]) -> int:
        """ 
        FinTracker and ForkWise accept csv inputs.
        Load csv from disk into a temporary staging table; calling function loads from the
        staging table into the relevant permanent table(s) in the db.

        WILL OVERWRITE STAGING IF ALREADY EXISTS!

        Parameters
        ----------
        csv_path : str
            path to csv of transactions or balances
        csv_columns : List[tuple[str]]
            Columns in the csv which become columns in the staging table.
            Each tuple in the list is (col_name, col_type), eg ('posted date', 'date').
            Note types need to be strings not classes (can be obtained by <type>.__name__)

        Returns
        -------
        int
            Length of a query of how many rows were added to the staging table

        """
        
        # Drop staging table if it already exists
        # This set of logic feels goofy ... 
        rows_before = 0
        try:
            rows_before = self.execute_scalar("SELECT COUNT(*) FROM staging;")
        except Exception as e:
            self._logger.debug(f"Query of staging table did not execute with exception: {e}")
        if rows_before is None:
            rows_before = 0
        if rows_before != 0:
            self._logger.info("Staging table still exists with content before loading new file")
            r = self.execute_action("DROP TABLE staging;")
            if r != "DROP TABLE":
                self._logger.error("Unable to drop staging table")
                raise ValueError("Unable to drop staging table before loading new file")
        
        col_and_type = ", ".join(f'{a} {b}' for a, b in csv_columns)
        r1 = self.execute_action(f"CREATE TABLE staging ({col_and_type}); ")
        if r1 != "CREATE TABLE":
            self._logger.error("Failed to create staging table")
            raise ValueError("Failed to create staging table before loading new file")

        r2 = self._import_file(dest_table="staging", path_to_file=csv_path)
        if r2==0: # This will happen if copy fails; eg if try to insert too many columns
            self._logger.info("No rows added to staging table")
            return 0

        # Query how many rows are now in staging table
        rows_after = self.execute_scalar("SELECT COUNT(*) FROM staging;")
        self._logger.info(f"After loading new transactions, staging has {rows_after} rows")

        return rows_after