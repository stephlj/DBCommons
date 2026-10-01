# Utilities for using dataclasses to enter data into or extract data from a db.
# 
# Dataclasses should be defined as follows:
#
# from dataclasses import dataclass, field
#
# def special_import_handling(input: str) -> str:
#    # If a csv row value needs special input handling that's beyond the capabilities 
#    # of a lambda function:
#    if input.lower()=='blah':
#        return 'blahblah' # or whatever
#    else:
#        return 'somethingelse'
#
# @dataclass
# class X:
#    field_that_is_a_number: float = field(metadata={'sql_type':'real', 'csv_parser': lambda s: float(s)})
#    field_needing_special_import: str = field(metadata={'sql_type':'text', 'csv_parser': special_import_handling})
#
# The way the field metadata works: 
# To return a list of tuples of (column name, sql type) for a NON-NESTED dataclass:
# col_defs_sql = [(f.name, f.metadata['sql_type']) for f in fields(X)]
# The same but returning python data types:
# col_defs_python = [(f.name, f.type.__name__) for f in fields(X)]
#
# This doesn't work for nested dataclasses, though, so a key utility here is
# flat_col_defs. This returns (field_name, sql_type) for a flat or nested
# dataclass. (No equivalent has been implemented for python types, since these 
# utilities define sql columns and types from dataclasses for import of data into the db).
# 
# Nested dataclasses are flattened recursively before csv schemas are defined.
# 
# Originally written by Claude, rewritten for clarity by Stephanie Johnson

import csv

from typing import TypeVar, Type, List, Tuple, Iterator, Any, get_type_hints
from dataclasses import fields, Field, is_dataclass

from dbcommons.utils import check_csv_path

# Assign a type, to be established when a function is called, to variable T.
# This is only used for type hints, but allows us to say: def func(input: T) -> T
# and indicate that the arg and return are both the same type. Using "Any"
# would lose track of that type. Since none of the dataclasses these utilities
# use are defined here, we can't define the type these functions handle
# until runtime.
T = TypeVar("T") 

def _fields_and_types(cls: type) -> Iterator[Tuple[Field, type]]:
    # Return each field of cls and its (python) type, using get_type_hints rather than f.type
    # so that string annotations, eg. from `from __future__ import annotations`, resolve properly.
    hints = get_type_hints(cls)
    for f in fields(cls):
        yield f, hints[f.name]

def _is_nested_dataclass(field_type: type) -> bool:
    # A nested dataclass is identified by the field's declared type being a dataclass.
    # This helper function identifies a dataclass field as another dataclass (ie, nesting),
    # and returns True if a field is another dataclass, false otherwise.
    # The input to this function should be a type hint from _fields_and_types.
    return is_dataclass(field_type)

def _leaf_fields(cls: type) -> Iterator[Field]:
    # Return the field if it's not a nested dataclass;
    # if it is, recurse.
    for f, field_type in _fields_and_types(cls):
        if _is_nested_dataclass(field_type=field_type):
            yield from _leaf_fields(field_type)
        else:
            yield f

def _from_flat_row(cls: Type[T], row: dict) -> T:
    # We make this a helper function even though it makes the logic 
    # of csv_to_dataclass harder to follow because then we can
    # make use of recursion for nested dataclasses:
    kwargs = {}
    for f, field_type in _fields_and_types(cls):
        if _is_nested_dataclass(field_type):
            kwargs[f.name] = _from_flat_row(field_type, row)
        else:
            kwargs[f.name] = f.metadata['csv_parser'](row[f.name])
    return cls(**kwargs)

def dataclass_to_flat_dict(obj: Any) -> dict:
    """
    Dict of {field name: field val} constructed from the dataclass instance `obj`,
    with any nested dataclasses flattened.
    """
    flat = {}
    for f, field_type in _fields_and_types(type(obj)):
        val = getattr(obj, f.name)
        if _is_nested_dataclass(field_type):
            flat.update(dataclass_to_flat_dict(val))
        else:
            flat[f.name] = val
    return flat

def flat_col_defs(cls: type) -> List[Tuple[str, str]]:
    """
    (name, sql_type) for how each field in `cls` maps to a column in the db.
    Nested dataclasses are flattened.
    """
    defs = [(f.name, f.metadata['sql_type']) for f in _leaf_fields(cls)]
    # We don't allow nested dataclass fields to have the same names as parent fields,
    # even if they're of different types
    names = [n for n,_ in defs]
    if len(names) != len(set(names)):
        raise ValueError("A nested dataclass has the same field name as the parent class; this isn't allowed!")
    return defs

def csv_to_dataclass(path_to_csv: str, cls: Type[T]) -> List[T]:
    """
    Load a csv into a list of `cls` objects, one per row.

    Correspondence is by name: every csv column must match a field name of `cls`
    (or a field name of a nested dataclass). Each field's metadata['csv_parser'] 
    turns the string cell into the field's value.

    Parameters
    ----------
    path_to_csv : str
        Path to a csv whose header holds every (flattened) field name of `cls`.
    cls : Type[T]
        A dataclass whose fields carry 'csv_parser' metadata.

    Returns
    -------
    List[T]
    """

    # Basic input checking
    check_csv_path(path_to_file=path_to_csv)

    # Expected columns are cls's (flattened) field names - the single source of
    # truth shared with the db staging col defs.
    expected_cols = [name for name, _ in flat_col_defs(cls)]

    with open(path_to_csv, mode='r') as f:
        reader = csv.DictReader(f)
        if set(reader.fieldnames or []) != set(expected_cols):
            msg = f"Wrong header in {path_to_csv}: needs to be {expected_cols} (instead of {reader.fieldnames})"
            raise ValueError(msg)

        return [_from_flat_row(cls, r) for r in reader]