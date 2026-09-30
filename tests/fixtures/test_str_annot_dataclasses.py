"""
Dataclasses with string annotations, for test_dataclass_utils.py.

Kept in their own module because `from __future__ import annotations` applies to
the whole module: putting it in test_dataclass_utils.py would turn every test
dataclass's annotations into strings. Classes must stay at module level, because
get_type_hints looks the strings up in this module's globals.

Written by Claude
"""
from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class StrAnnotGizmo:
    label: str = field(metadata={'sql_type': 'text', 'csv_parser': lambda s: s})
    weight: float = field(metadata={'sql_type': 'real', 'csv_parser': lambda s: float(s)})

@dataclass
class StrAnnotNestedGizmo:
    name: str = field(metadata={'sql_type': 'text', 'csv_parser': lambda s: s})
    gizmo: StrAnnotGizmo  # f.type is the string 'StrAnnotGizmo', not the class