"""Guards on the package itself: no float literals, no I/O, no clock, no other app packages."""

import ast
import io
import tokenize
from pathlib import Path

import app.calc

PACKAGE = Path(app.calc.__file__).parent
SOURCES = sorted(PACKAGE.glob("*.py"))
ALLOWED_IMPORTS = {
    "__future__", "calendar", "collections", "dataclasses", "datetime", "decimal", "json", "typing", "pydantic",
}


def test_there_are_sources_to_check():
    assert len(SOURCES) >= 10


def test_no_float_literals_anywhere():
    found = []
    for path in SOURCES:
        for tok in tokenize.generate_tokens(io.StringIO(path.read_text()).readline):
            if tok.type == tokenize.NUMBER and not tok.string.lower().startswith(("0x", "0b", "0o")):
                if any(c in tok.string.lower() for c in ".ej"):
                    found.append(f"{path.name}:{tok.start[0]} {tok.string}")
    assert found == []


def test_float_is_only_named_to_refuse_it():
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Name) and node.id == "float":
                line = path.read_text().splitlines()[node.lineno - 1]
                assert "isinstance(" in line, f"{path.name}:{node.lineno} {line.strip()}"


def test_imports_are_stdlib_pydantic_or_this_package():
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # relative: inside app.calc
                    assert node.level == 1, f"{path.name}:{node.lineno} reaches outside the package"
                    continue
                roots = [(node.module or "").split(".")[0]]
            else:
                continue
            for root in roots:
                assert root in ALLOWED_IMPORTS, f"{path.name}:{node.lineno} imports {root}"


def test_no_clock_file_or_network_calls():
    banned_calls = {"open", "print", "input", "eval", "exec"}
    banned_attrs = {"now", "today", "utcnow"}
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls, f"{path.name}:{node.lineno} calls {node.func.id}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs, f"{path.name}:{node.lineno} calls .{node.func.attr}()"
