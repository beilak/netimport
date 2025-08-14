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
