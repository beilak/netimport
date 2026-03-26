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

    assert "os" in imports
    assert "sys" in imports
    assert "collections.defaultdict" in imports
    assert ".sibling" in imports
    assert ".module.name" in imports
    assert "..package.another_name" in imports
    assert "package.module" in imports
    assert "package" in imports
    assert "." in imports


def test_get_imported_modules_skips_type_checking_imports_by_default(tmp_path: Path) -> None:
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


def test_get_imported_modules_can_include_type_checking_imports(tmp_path: Path) -> None:
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
