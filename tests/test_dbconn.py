# Copyright (c) 2026 Stephanie Johnson

import unittest
import os

from dataclasses import dataclass, fields
from psycopg import sql

import dbcommons.testing_utils as utils
from dbcommons.db_conn import DBConn

@dataclass
class TestClass:
    fruit: str
    nums: float

    def __iter__(self):
        yield self.fruit
        yield self.nums

class TestDBConn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db; implicit test of init_db and add_user.
        cls.params = utils.config_params()
        utils.set_up_test_DB(params=cls.params)
        cls._conn = DBConn(user=cls.params["user"], pw=cls.params["user_pw"], db_name=cls.params["test_db_name"])

        cls.csv_cols = [('fruit','text'), ('nums', 'real')]
        cls.col_types = ", ".join(f'{b}' for _, b in cls.csv_cols)

    @classmethod
    def tearDownClass(cls):
        utils.tear_down_test_DB(db_conn=cls._conn, params=cls.params)
    
    def test_import_csv(self):
        # Does it work at all - see test_csv_to_staging
        
        # Does it raise the right exceptions
        with self.assertRaises(ValueError): 
            self._conn._import_csv(col_types=self.col_types, dest_table="staging", path_to_file=os.path.join(utils.TEST_DATA_PATH, "blah.csv"))
        
        with self.assertRaises(ValueError):
            self._conn._import_csv(col_types=self.col_types, dest_table="staging", path_to_file=os.path.join(utils.TEST_DATA_PATH, "test_config.yml"))
        
    
    def test_csv_to_staging(self):
        self.addCleanup(self._conn.execute_action, "DROP TABLE staging;")

        # Implicit test of _import_csv, create_staging as well as execute_action, execute_scalar
        self._conn.create_staging(col_defs=self.csv_cols)
        self._conn.csv_to_staging(csv_path=os.path.join(utils.TEST_DATA_PATH, "test.csv"),csv_columns=self.csv_cols)

        # Implicit test of execute_query
        self.assertEqual(len(self._conn.execute_query("SELECT * FROM staging;")), 3, "Incorrect number of rows imported from csv to staging")

        # Implicit test of execute_scalar
        self.assertEqual(self._conn.execute_scalar("SELECT nums FROM staging WHERE fruit='Banana';"), 2.02)

    def test_execute_query(self):
        r = self._conn.execute_query("INSERT INTO test_table (fruit, nums) VALUES (%s, %s) RETURNING *;", ('tomato',4.04))
        self.assertEqual(r[0]['fruit'],'tomato')

    def test_execute_query_w_classs(self):

        q = sql.SQL("INSERT INTO test_table ({cols}) VALUES (%s, %s) RETURNING {cols};").format(cols=sql.SQL(",").join([sql.Identifier(f.name) for f in fields(TestClass)]))
        r = self._conn.execute_query_w_class(query=q, return_class=TestClass, vals=('watermelon',5.05))
        self.assertEqual(r[0].fruit,'watermelon')

    def test_insert_many_w_class(self):
        self.addCleanup(self._conn.execute_action, "DROP TABLE test_table;")
        
        create_q = sql.SQL("CREATE TABLE test_table ({cols});").format(cols=sql.SQL(",").join(f'{sql.Identifier(f.name)} {sql.Identifier(f.type.__name__)}' for f in fields(TestClass)))
        self._conn.execute_action(create_q)

        test_class_list = [TestClass(fruit='blackberry', nums=100.1), TestClass(fruit='blueberry', nums=200.2)]
        
        r = self._conn.insert_many_w_class(tablename='test_table', insert_cls=test_class_list)
        self.assertEqual(r, 2)
        