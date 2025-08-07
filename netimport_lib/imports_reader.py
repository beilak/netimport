import ast
import os


class ImportItem:
    def __init__(
        self,
        module_path: str | None,
        name: str | None,
        alias: str | None,
        level: int,
        lineno: int,
        col_offset: int,
        is_type_checking: bool = False,
    ) -> None:
        self.module_path = module_path
        self.name = name
        self.alias = alias
        self.level = level
        self.lineno = lineno
        self.col_offset = col_offset
        self.is_type_checking = is_type_checking

    def __repr__(self) -> str:
        return (
            f"ImportItem(module_path={self.module_path!r}, name={self.name!r}, "
            f"alias={self.alias!r}, level={self.level}, L{self.lineno}, "
            f"type_checking={self.is_type_checking})"
        )

    @property
    def full_imported_name(self) -> str:
        """Return str for imported name
        - "os" for `import os`
        - "package.module" for `import package.module`
        - "package.module.name" for `from package.module import name`
        - ".sibling" for `from . import sibling`
        - ".module.name" for `from .module import name`
        - "package" for `from package import *`
        - "." for `from . import *`.
        """
        prefix = "." * self.level

        # Case 1: from ... import name
        if self.name and self.name != "*":
            if self.module_path:
                return f"{prefix}{self.module_path}.{self.name}"
            return f"{prefix}{self.name}"

        # Case 2: import module.path OR from module.path import *
        if self.module_path:  # e.g. "os", "package.module"
            return f"{prefix}{self.module_path}"

        # Case 3: from . import * (или from .. import *, и т.д.)
        if self.name == "*" and not self.module_path and self.level > 0:
            return prefix  # "." or ".."

        # Case 4 from . import (без имени и без *)
        if not self.module_path and not self.name and self.level > 0:
            return prefix

        return ""


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.imports: list[ImportItem] = []
        self._in_type_checking_block = False

    def _extract_imports(
        self,
        node_names: list[ast.alias],
        module_base: str | None,
        level: int,
        lineno: int,
        col_offset: int,
    ) -> None:
        for alias_node in node_names:
            imported_name = alias_node.name
            alias = alias_node.asname

            current_module_path: str | None
            current_name: str | None

            if module_base is None:  # for `import foo` or `import foo.bar`
                current_module_path = imported_name
                current_name = None
            else:  # for `from foo import bar`
                current_module_path = module_base
                current_name = imported_name

            self.imports.append(
                ImportItem(
                    module_path=current_module_path,
                    name=current_name,
                    alias=alias,
                    level=level,
                    lineno=lineno,
                    col_offset=col_offset,
                    is_type_checking=self._in_type_checking_block,
                )
            )

    def visit_Import(self, node: ast.Import) -> None:
        self._extract_imports(
            node.names,
            module_base=None,
            level=0,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_base = node.module if node.module else ""
        level = node.level
        self._extract_imports(
            node.names,
            module_base=module_base,
            level=level,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        is_type_checking_if = False
        # for if TYPE_CHECKING:
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            is_type_checking_if = True

        elif isinstance(node.test, ast.Attribute):
            current = node.test
            while isinstance(current, ast.Attribute):
                if current.attr == "TYPE_CHECKING":
                    is_type_checking_if = True
                    break
                current = current.value
            if isinstance(current, ast.Name) and current.id == "TYPE_CHECKING":
                is_type_checking_if = True

        original_in_type_checking_block = self._in_type_checking_block
        if is_type_checking_if:
            self._in_type_checking_block = True

        for stmt in node.body:
            self.visit(stmt)

        if is_type_checking_if:
            self._in_type_checking_block = original_in_type_checking_block

        for stmt in node.orelse:
            self.visit(stmt)


def get_imported_modules_as_strings(
    file_path: str, include_type_checking_imports: bool = False
) -> list[str]:
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return []

    try:
        with open(file_path, encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code, filename=file_path)

    except Exception:
        return []

    visitor = ImportVisitor(file_path)
    visitor.visit(tree)

    imported_module_names: list[str] = []
    for imp_item in visitor.imports:
        if not include_type_checking_imports and imp_item.is_type_checking:
            continue

        full_name = imp_item.full_imported_name
        if full_name:
            imported_module_names.append(full_name)

    return sorted(imported_module_names)
