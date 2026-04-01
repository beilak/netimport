from pathlib import Path

from netimport_lib.imports_reader import get_imported_modules_as_strings


def test_get_imported_modules_as_strings(tmp_path: Path) -> None:
    dummy_file = tmp_path / "dummy_file.py"
    dummy_file.write_text(
        """
import os
import sys
from collections import defaultdict
from . import sibling
from .module import name
from ..package import another_name
import package.module
from package import *
from . import *
"""
    )

    imports = get_imported_modules_as_strings(str(dummy_file))

    assert set(imports) == {
        "os",
        "sys",
        "collections.defaultdict",
        ".sibling",
        ".module.name",
        "..package.another_name",
        "package.module",
        "package",
        ".",
    }


def test_skip_type_checking_by_default(tmp_path: Path) -> None:
    dummy_file = tmp_path / "dummy_type_checking.py"
    dummy_file.write_text(
        """
from typing import TYPE_CHECKING
import os
import typing

if TYPE_CHECKING:
    import pandas

if typing.TYPE_CHECKING:
    from app import models
"""
    )

    imports = get_imported_modules_as_strings(str(dummy_file))

    assert "os" in imports
    assert "typing" in imports
    assert "typing.TYPE_CHECKING" in imports
    assert "pandas" not in imports
    assert "app.models" not in imports


def test_get_imports_include_type_checking(tmp_path: Path) -> None:
    dummy_file = tmp_path / "dummy_type_checking.py"
    dummy_file.write_text(
        """
from typing import TYPE_CHECKING
import typing

if TYPE_CHECKING:
    import pandas

if typing.TYPE_CHECKING:
    from app import models
"""
    )

    imports = get_imported_modules_as_strings(
        str(dummy_file),
        include_type_checking_imports=True,
    )

    assert "pandas" in imports
    assert "app.models" in imports
