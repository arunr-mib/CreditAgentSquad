"""A small evaluator for the formulas this package writes into workbooks, so the verifier can
recompute every formula cell from the input cells without Excel.

Supports numbers, cell references (with or without a sheet name), ranges inside SUM, the
operators + - * /, unary minus, brackets, and SUM, ROUND and ABS. Arithmetic is decimal at 50
digits and ROUND is half-up, as in `app.calc`. A reference to an empty cell is an error: a
missing input is never zero.
"""
import re
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Context, Decimal

CTX = Context(prec=50)
_TOKEN = re.compile(r"""
    \s*(?:
      (?P<num>\d+(?:\.\d+)?)
    | (?P<ref>(?:(?:'(?P<qsheet>[^']+)'|(?P<sheet>[A-Za-z_][\w.]*))!)?\$?(?P<col>[A-Z]{1,3})\$?(?P<row>\d+)
        (?::\$?(?P<col2>[A-Z]{1,3})\$?(?P<row2>\d+))?)
    | (?P<func>[A-Z]+)\(
    | (?P<op>[-+*/(),])
    )""", re.X)


class FormulaError(ValueError):
    pass


def col_number(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def col_letters(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def tokenize(text: str) -> list[tuple[str, dict]]:
    tokens, pos = [], 0
    text = text.lstrip("=")
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None or m.end() == pos:
            if text[pos:].strip() == "":
                break
            raise FormulaError(f"cannot read formula at {text[pos:pos + 12]!r}")
        pos = m.end()
        if m.group("num") is not None:
            tokens.append(("num", {"value": Decimal(m.group("num"))}))
        elif m.group("ref") is not None:
            tokens.append(("ref", {"sheet": m.group("qsheet") or m.group("sheet"), "col": m.group("col"),
                                   "row": int(m.group("row")), "col2": m.group("col2"),
                                   "row2": int(m.group("row2")) if m.group("row2") else None}))
        elif m.group("func") is not None:
            tokens.append(("func", {"name": m.group("func")}))
        else:
            tokens.append(("op", {"value": m.group("op")}))
    return tokens


def references(text: str, sheet: str) -> list[tuple[str, str]]:
    """Every cell a formula reads, as (sheet, address)."""
    out = []
    for kind, tok in tokenize(text):
        if kind != "ref":
            continue
        name = tok["sheet"] or sheet
        if tok["col2"] is None:
            out.append((name, f"{tok['col']}{tok['row']}"))
        else:
            for c in range(col_number(tok["col"]), col_number(tok["col2"]) + 1):
                for r in range(tok["row"], tok["row2"] + 1):
                    out.append((name, f"{col_letters(c)}{r}"))
    return out


def evaluate(text: str, sheet: str, cell: Callable[[str, str], Decimal | None]) -> Decimal:
    """Evaluate a formula. `cell(sheet, address)` returns the cell's value, or None when empty."""
    tokens = tokenize(text)
    pos = 0

    def peek() -> tuple[str, dict] | None:
        return tokens[pos] if pos < len(tokens) else None

    def take_op(value: str) -> bool:
        nonlocal pos
        tok = peek()
        if tok and tok[0] == "op" and tok[1]["value"] == value:
            pos += 1
            return True
        return False

    def read(name: str, address: str) -> Decimal:
        value = cell(name, address)
        if value is None:
            raise FormulaError(f"{name}!{address} is empty")
        return value

    def cells(tok: dict) -> list[Decimal]:
        name = tok["sheet"] or sheet
        if tok["col2"] is None:
            return [read(name, f"{tok['col']}{tok['row']}")]
        return [read(name, f"{col_letters(c)}{r}")
                for c in range(col_number(tok["col"]), col_number(tok["col2"]) + 1)
                for r in range(tok["row"], tok["row2"] + 1)]

    def args() -> list[list[Decimal]]:
        out = []
        if take_op(")"):
            return out
        while True:
            tok = peek()
            if tok and tok[0] == "ref" and tok[1]["col2"] is not None:
                nonlocal pos
                pos += 1
                out.append(cells(tok[1]))
            else:
                out.append([expr()])
            if take_op(")"):
                return out
            if not take_op(","):
                raise FormulaError("expected , or ) in a function")

    def atom() -> Decimal:
        nonlocal pos
        tok = peek()
        if tok is None:
            raise FormulaError("formula ends early")
        kind, data = tok
        pos += 1
        if kind == "num":
            return data["value"]
        if kind == "ref":
            if data["col2"] is not None:
                raise FormulaError("a range is only allowed inside SUM")
            return cells(data)[0]
        if kind == "func":
            values = args()
            if data["name"] == "SUM":
                total = Decimal(0)
                for group in values:
                    for v in group:
                        total = CTX.add(total, v)
                return total
            if data["name"] == "ROUND" and len(values) == 2:
                places = int(values[1][0])
                return values[0][0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
            if data["name"] == "ABS" and len(values) == 1:
                return abs(values[0][0])
            raise FormulaError(f"function {data['name']} is not supported")
        if data["value"] == "(":
            value = expr()
            if not take_op(")"):
                raise FormulaError("missing )")
            return value
        if data["value"] == "-":
            return -atom()
        if data["value"] == "+":
            return atom()
        raise FormulaError(f"unexpected {data['value']!r}")

    def term() -> Decimal:
        value = atom()
        while True:
            if take_op("*"):
                value = CTX.multiply(value, atom())
            elif take_op("/"):
                divisor = atom()
                if divisor == 0:
                    raise FormulaError("division by zero")
                value = CTX.divide(value, divisor)
            else:
                return value

    def expr() -> Decimal:
        value = term()
        while True:
            if take_op("+"):
                value = CTX.add(value, term())
            elif take_op("-"):
                value = CTX.subtract(value, term())
            else:
                return value

    result = expr()
    if pos != len(tokens):
        raise FormulaError("formula has trailing text")
    return result
