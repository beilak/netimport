"""AST-based import extraction for Python source files."""

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class _ImportItem:
    module_path: str | None
    name: str | None
    level: int
    is_type_checking: bool = False

    @property
    def full_imported_name(self) -> str:
        prefix = "." * self.level

        if self.name and self.name != "*":
            if self.module_path:
                return f"{prefix}{self.module_path}.{self.name}"
            return f"{prefix}{self.name}"

        if self.module_path:
            return f"{prefix}{self.module_path}"

        if self.level > 0:
            return prefix

        return ""


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[_ImportItem] = []
        self._in_type_checking_block = False

    def visit_Import(self, node: ast.Import) -> None:
        self._extract_imports(node.names, None, level=0)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._extract_imports(node.names, node.module, level=node.level)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        is_type_checking_if = _is_type_checking_test(node.test)
        previous_state = self._in_type_checking_block

        if is_type_checking_if:
            self._in_type_checking_block = True

        for statement in node.body:
            self.visit(statement)

        self._in_type_checking_block = previous_state

        for statement in node.orelse:
            self.visit(statement)

    def _extract_imports(
        self,
        node_names: list[ast.alias],
        module_base: str | None,
        *,
        level: int,
    ) -> None:
        for alias_node in node_names:
            imported_name = alias_node.name

            current_module_path: str | None
            current_name: str | None

            if module_base is None and level == 0:
                current_module_path = imported_name
                current_name = None
            else:
                current_module_path = module_base
                current_name = imported_name

            self.imports.append(
                _ImportItem(
                    module_path=current_module_path,
                    name=current_name,
                    level=level,
                    is_type_checking=self._in_type_checking_block,
                )
            )


def _is_type_checking_test(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    if isinstance(node, ast.Attribute):
        return node.attr == "TYPE_CHECKING"
    return False


def _parse_source_tree(path: Path, file_path: str) -> ast.AST | None:
    try:
        source_code = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    try:
        return ast.parse(source_code, filename=file_path)
    except SyntaxError:
        return None


def _collect_imported_names(
    visitor: _ImportVisitor,
    include_type_checking_imports: bool,
) -> list[str]:
    imported_module_names: list[str] = []

    for import_item in visitor.imports:
        if not include_type_checking_imports and import_item.is_type_checking:
            continue

        imported_name = import_item.full_imported_name
        if imported_name:
            imported_module_names.append(imported_name)
    return imported_module_names


def get_imported_modules_as_strings(
    file_path: str,
    include_type_checking_imports: bool = False,
) -> list[str]:
    """Return imported module names extracted from a Python file."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return []

    tree = _parse_source_tree(path, file_path)
    if tree is None:
        return []

    visitor = _ImportVisitor()
    visitor.visit(tree)
    return sorted(_collect_imported_names(visitor, include_type_checking_imports))
