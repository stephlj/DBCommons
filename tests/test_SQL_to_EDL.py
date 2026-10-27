# test_SQL_to_EDL.py
#
# Copyright (c) 2025 Stephanie Johnson

import unittest
import os

import dbcommons.testing_utils as utils
from dbcommons.SQL_to_EDL import convert_to_EDL

class TestEDLConverter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sql_file_path = os.path.join(utils.TEST_DATA_PATH,"test_SQL_schema.sql")
        cls.correct_output_path = os.path.join(utils.TEST_DATA_PATH,"test_EDL_schema.txt")
        cls.new_output_path = os.path.splitext(cls.sql_file_path)[0]+"_EDL.txt"
    
    @classmethod
    def tearDownClass(cls):
        if os.path.isfile(cls.new_output_path):
            os.remove(cls.new_output_path)

    def test_convert_name(self):
        # TODO implement a test for this function
        pass
    
    def test_SQL_to_EDL(self):
        
        converted_path = convert_to_EDL(self.sql_file_path)

        with open(converted_path, "r") as f1:
            converted_lines = [line.strip() for line in f1.read().splitlines() if line.strip() and line!="-"]

        with open(self.correct_output_path, "r") as f2:
            correct_lines = [line.strip() for line in f2.read().splitlines() if line.strip()and line!="-"]

        combined = set(converted_lines) & set(correct_lines) # Keep all lines that are in both test and ground truth

        self.assertEqual(len(combined), len(correct_lines), "Converted SQL and ground truth EDL do not match")