import unittest
import os, tempfile

from dataclasses import dataclass, field, fields

from dbcommons.dataclass_utils import flat_col_defs, dataclass_to_flat_dict, csv_to_dataclass
from fixtures.test_str_annot_dataclasses import StrAnnotGizmo, StrAnnotNestedGizmo

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), "fixtures")

# Creating a string-strip function to test passing named functions (not just lambdas) in csv_parser
def str_strip(input: str) -> str:
    return input.strip()

# Some silly dataclasses to use for testing:
@dataclass
class FlatGizmo:
    label: str = field(metadata={'sql_type': 'text', 'csv_parser': lambda s: s})
    weight: float = field(metadata={'sql_type': 'real', 'csv_parser': lambda s: float(s)})
    shiny: bool = field(metadata={'sql_type': 'boolean', 'csv_parser': lambda s: bool(int(s))})
    size_units: str = field(metadata={'sql_type': 'text', 'csv_parser': str_strip})

@dataclass
class NestedGizmo:
    length: float = field(metadata={'sql_type': 'real', 'csv_parser': lambda s: float(s)})
    width: float = field(metadata={'sql_type': 'real', 'csv_parser': lambda s: float(s)})
    unit_category: str = field(metadata={'sql_type': 'text', 'csv_parser': lambda s: s.strip()})

@dataclass
class Gizmo:
    label: str = field(metadata={'sql_type': 'text', 'csv_parser': lambda s: s})
    weight: float = field(metadata={'sql_type': 'real', 'csv_parser': lambda s: float(s)})
    shiny: bool = field(metadata={'sql_type': 'boolean', 'csv_parser': lambda s: bool(int(s))})
    size_info: NestedGizmo

@dataclass
class GizmoDupName:
    unit_category: str = field(metadata={'sql_type': 'text', 'csv_parser': lambda s: s})
    weight: float = field(metadata={'sql_type': 'real', 'csv_parser': lambda s: float(s)})
    shiny: bool = field(metadata={'sql_type': 'boolean', 'csv_parser': lambda s: bool(int(s))})
    size_info: NestedGizmo

class TestDataclassUtils(unittest.TestCase):

    def _write_tmp_csv(self, text: str) -> str:
        # Write `text` to a throwaway .csv and return its path (cleaned up after the test).

        f = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        f.write(text)
        f.close()

        self.addCleanup(os.remove, f.name)
        
        return f.name
    
    def test_flat_col_defs(self):
        with self.subTest("Test an unested dataclass resolves fine"):
            # A dataclass with no nested dataclass field is just its own (name, sql_type) pairs.
            self.assertEqual(flat_col_defs(FlatGizmo), [
                ('label', 'text'),
                ('weight', 'real'),
                ('shiny', 'boolean'),
                ('size_units', 'text'),
            ])
        
        with self.subTest("Test nested dataclass flattens"):
            defs = flat_col_defs(Gizmo)
            self.assertEqual(defs, [
                ('label', 'text'),
                ('weight', 'real'),
                ('shiny', 'boolean'),
                ('length', 'real'),
                ('width', 'real'),
                ('unit_category', 'text'),
            ])
            self.assertNotIn('size_info', [name for name, _ in defs]) # The name of the nested dataclass shouldn't appear

        with self.subTest("Test that we error if the nested dataclass has a name clash"):
            with self.assertRaises(ValueError):
                defs = flat_col_defs(GizmoDupName)

        # Test that we can resolve dataclasses from modules with `from __future__ import annotations`
        # First: make sure the test is still set up correctly:
        # if the __future__ import is ever removed from str_annot_dataclasses,
        # the tests below would still pass without exercising string resolution.
        self.assertEqual(fields(StrAnnotNestedGizmo)[1].type, 'StrAnnotGizmo')

        with self.subTest("Test string annotations resolve correctly"):
            self.assertEqual(flat_col_defs(StrAnnotNestedGizmo),
                         [('name', 'text'), ('label', 'text'), ('weight', 'real')])
        
    def test_dataclass_to_flat_dict(self):
        flat_obj = FlatGizmo(label='inner',weight=1.5,shiny=False,size_units='lb')
        with self.subTest("Test an unnested dataclass"):
            self.assertEqual(dataclass_to_flat_dict(flat_obj),
                             {'label':'inner','weight':1.5,'shiny':False,'size_units':'lb'})

        nested_obj = Gizmo(label='outer', weight=2.0, shiny=True, size_info=NestedGizmo(length=20.2, width=5.5, unit_category='length'))
        with self.subTest("Test a nested dataclass"):
            self.assertEqual(dataclass_to_flat_dict(nested_obj),
                             {'label':'outer', 'weight':2.0, 'shiny':True, 'length':20.2, 'width':5.5, 'unit_category':'length'})

        # Test that we can resolve dataclasses from modules with `from __future__ import annotations`
        # First: make sure the test is still set up correctly:
        # if the __future__ import is ever removed from str_annot_dataclasses,
        # the tests below would still pass without exercising string resolution.
        self.assertEqual(fields(StrAnnotNestedGizmo)[1].type, 'StrAnnotGizmo')
        obj = StrAnnotNestedGizmo(name='outer', gizmo=StrAnnotGizmo(label='Sprocket', weight=2.5))
        with self.subTest("Test string annotations resolve correctly when flattening"):
            self.assertEqual(dataclass_to_flat_dict(obj),
                         {'name': 'outer', 'label': 'Sprocket', 'weight': 2.5})

    def test_csv_to_dataclass(self):
        # Test generic behavior loading csvs to a dataclass.
        # Note the csv columns are in a different order than *Gizmo's fields: correspondence
        # is by name, so order shouldn't matter.
        gizmos = csv_to_dataclass(
            path_to_csv=os.path.join(TEST_DATA_PATH, "test_arbitrary_dataclass.csv"), cls=FlatGizmo)

        self.assertEqual(gizmos[0].label, "Sprocket")     # str passthrough
        self.assertEqual(gizmos[0].weight, 2.5)           # float parser
        self.assertTrue(gizmos[0].shiny)                  # '1' -> bool(int) -> True
        self.assertFalse(gizmos[1].shiny)                 # '0' -> False (not the truthy-string bug)
        self.assertEqual(gizmos[0].size_units, "c")       # ' c' -> 'c', from a non-lamba function

        # Wrong value type in a row: non-numeric where float is expected -> ValueError.
        with self.subTest("wrong value type"):
            path = self._write_tmp_csv("shiny,size_units,label,weight\n1,cup,Sprocket,heavy\n")
            with self.assertRaises(ValueError):
                csv_to_dataclass(path_to_csv=path, cls=FlatGizmo)

        # No header: DictReader treats the first (data) row as the header, so the column
        # names won't match the expected fields -> ValueError.
        with self.subTest("no header"):
            path = self._write_tmp_csv("1,cup,Sprocket,2.5\n0,lb,Widget,10\n")
            with self.assertRaises(ValueError):
                csv_to_dataclass(path_to_csv=path, cls=FlatGizmo)

        # Wrong header - easy-to-miss trailing whitespace in a column name.
        with self.subTest("whitespace in header name"):
            path = self._write_tmp_csv("shiny,size_units,label,weight \n1,cup,Sprocket,2.5\n")
            with self.assertRaises(ValueError):
                csv_to_dataclass(path_to_csv=path, cls=FlatGizmo)

        # Empty file: reader.fieldnames is None -> guarded by `or []` -> ValueError, not TypeError.
        with self.subTest("empty file"):
            path = self._write_tmp_csv("")
            with self.assertRaises(ValueError):
                csv_to_dataclass(path_to_csv=path, cls=FlatGizmo)

        # Load a csv corresponding to a nested dataclass and its parent
        nested_gizmo = csv_to_dataclass(
                    path_to_csv=os.path.join(TEST_DATA_PATH, "test_nested_dataclass.csv"), cls=Gizmo)

        self.assertEqual(nested_gizmo[0].label, 'Inner')        # str passthrough
        self.assertEqual(nested_gizmo[0].weight, 1.5)           # float parser
        self.assertTrue(nested_gizmo[1].shiny)                  # '1' -> bool(int) -> True
        self.assertFalse(nested_gizmo[0].shiny)                 # '0' -> False (not the truthy-string bug)
        self.assertEqual(nested_gizmo[0].size_info.length, 10.5)          # nested value
        self.assertEqual(nested_gizmo[1].size_info.unit_category, 'c')     # ' c' -> 'c', from a lamba function

        # Test nested dataclasses with string annotation
        path = self._write_tmp_csv("weight,name,label\n2.5,outer,Sprocket\n")
        # TODO I think this assertion is wrong?
        self.assertEqual(csv_to_dataclass(path_to_csv=path, cls=StrAnnotNestedGizmo),
                         [StrAnnotNestedGizmo(name='outer', gizmo=StrAnnotGizmo(label='Sprocket', weight=2.5))])

