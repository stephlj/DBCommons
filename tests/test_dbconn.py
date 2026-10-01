# Copyright (c) 2026 Stephanie Johnson

import unittest
import os

from dataclasses import dataclass, fields, field
from psycopg import sql

import dbcommons.testing_utils as utils
from dbcommons.dataclass_utils import flat_col_defs
from dbcommons.db_conn import DBConn

@dataclass
class Preferences:
    mama_bear: bool = field(metadata={'sql_type':'boolean'})
    papa_bear: bool = field(metadata={'sql_type':'boolean'})
    baby_bear: bool = field(metadata={'sql_type':'boolean'})

    def __iter__(self):
        yield self.mama_bear
        yield self.papa_bear
        yield self.baby_bear

@dataclass
class FruitClass:
    fruit: str = field(metadata={'sql_type':'text'})
    nums: float = field(metadata={'sql_type':'real'})

    def __iter__(self):
        yield self.fruit
        yield self.nums

@dataclass
class NestedFruit:
    fruit: str = field(metadata={'sql_type':'text'})
    nums: float = field(metadata={'sql_type':'real'})
    prefs: Preferences

    def __iter__(self):
        yield self.fruit
        yield self.nums
        yield self.prefs


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
        # Does it raise the right exceptions
        # These are actually tests for utils.check_csv_path
        # TODO add some testing coverage for mismatches between col_types here and 
        # what's in the csv, dest_table not existing and such. Not bothering for now
        # since _import_csv is mostly deprecated now.
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

    def test_execute_query_w_class(self):

        q = sql.SQL("INSERT INTO test_table ({cols}) VALUES (%s, %s) RETURNING {cols};").format(cols=sql.SQL(",").join([sql.Identifier(f.name) for f in fields(FruitClass)]))
        r = self._conn.execute_query_w_class(query=q, return_class=FruitClass, vals=('watermelon',5.05))
        self.assertEqual(r[0].fruit,'watermelon')

    def test_insert_many_w_class(self):
        # Implicit test of dataclass_to_flat_dict for non-nested
        self.addCleanup(self._conn.execute_action, "DROP TABLE staging;")
        
        self._conn.create_staging(col_defs=[(f.name, f.metadata['sql_type']) for f in fields(FruitClass)])

        test_class_list = [FruitClass(fruit='blackberry', nums=100.1), FruitClass(fruit='blueberry', nums=200.2)]
        
        r = self._conn.insert_many_w_class(tablename='staging', insert_cls=test_class_list)
        self.assertEqual(r, 2)

    def test_insert_many_w_class_nested(self):
        # Implicit tests of flat_col_defs, dataclass_to_flat_dict
        self.addCleanup(self._conn.execute_action, "DROP TABLE staging;")
                
        self._conn.create_staging(col_defs=flat_col_defs(cls=NestedFruit))

        test_class_list = [NestedFruit(fruit='blackberry', 
                                       nums=100.1, 
                                       prefs=Preferences(mama_bear=True,
                                                         papa_bear=False,
                                                         baby_bear=True)), 
                           NestedFruit(fruit='blueberry', 
                                       nums=200.2,
                                       prefs=Preferences(mama_bear=False,
                                                        papa_bear=True,
                                                        baby_bear=False))]
        
        r = self._conn.insert_many_w_class(tablename='staging', insert_cls=test_class_list)
        self.assertEqual(r, 2)
        self.assertFalse(self._conn.execute_scalar(query="SELECT baby_bear FROM staging WHERE fruit=%s", vals=('blueberry',)))
        