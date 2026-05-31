# Copyright (c) 2026 Stephanie Johnson

import unittest
import os
import errno

import dbcommons.testing_utils as utils
from dbcommons.db_conn import DBConn

class TestDBConn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db; implicit test of init_db and add_user.
        cls.params = utils.config_params()
        utils.set_up_test_DB(params=cls.params)
        cls.conn = DBConn(user=cls.params["user"], pw=cls.params["user_pw"], db_name=cls.params["test_db_name"])

        cls.csv_cols = [('fruit','text'), ('nums', 'real')]
        cls.col_types = ", ".join(f'{b}' for _, b in cls.csv_cols)

    @classmethod
    def tearDownClass(cls):
        utils.tear_down_test_DB(db_conn=cls.conn, params=cls.params)
    
    def test_import_csv(self):
        # Does it work at all - see test_csv_to_staging
        
        # Does it raise the right exceptions
        # with self.assertRaises(errno.ENOENT): # ENOENT = FileNotFoundError. But this doesn't work cuz errno isn't an exception ... 
        #     self.conn._import_csv(col_types=self.col_types, dest_table="staging", path_to_file=os.path.join(utils.TEST_DATA_PATH, "blah.csv"))
        
        with self.assertRaises(ValueError):
            self.conn._import_csv(col_types=self.col_types, dest_table="staging", path_to_file=os.path.join(utils.TEST_DATA_PATH, "test_config.yml"))
        
    
    def test_csv_to_staging(self):
        self.addCleanup(self.conn.execute_action, "DROP TABLE staging;")

        self.conn.csv_to_staging(csv_path=os.path.join(utils.TEST_DATA_PATH, "test.csv"),csv_columns=self.csv_cols)

        # Implicit test of execute_query
        self.assertEqual(len(self.conn.execute_query("SELECT * FROM staging;")), 3, "Incorrect number of rows imported from csv to staging")

        # Implicit test of execute_scalar
        self.assertEqual(self.conn.execute_scalar("SELECT nums FROM staging WHERE fruit='Banana';"), 2.02)