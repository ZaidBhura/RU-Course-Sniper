"""Parse and evaluate the free-text prerequisite notes from the Rutgers SOC API.

SOC `preReqNotes` look like:

    ((01:198:112 DATA STRUCTURES  or 14:332:351 PROGRM METHODOLOGYII ) and
     (01:198:206 INTRODUCTION TO DISCRETE STRUCTURES II ))<em> OR </em> (...)

Observed conventions (Fall 2026 NB file, 1,234 courses with notes):
- Titles are uppercase and may contain "AND", commas, and parentheses like "(CSW)".
- Connectors inside a group are lowercase `and` / `or`.
- Connectors between groups are `<em> OR </em>` / `<em> AND </em>`.
- A closing paren that ends a group is always preceded by whitespace.
- Special forms:
    "Any Course EQUAL or GREATER Than: (01:640:112 ...)"
    "Any Two Course from the following: (A ) (B ) (C )"
    "TWO Course Within the Subject Area:"  (no courses listed; not machine-checkable)

The parsed tree is plain JSON so it can be stored in a JSONB column:

    {"type": "course", "course": "01:198:112"}
    {"type": "all", "of": [...]}          every child required
    {"type": "any", "of": [...]}          at least one child required
    {"type": "n_of", "n": 2, "of": [...]} at least n children required
    {"type": "at_least", "course": "01:640:112"}
        any course in the same school:subject numbered >= the given one
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

PrereqNode = dict[str, Any]

COURSE_RE = re.compile(r"\d{2}:\d{3}:\d{3}")

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

_TOP_CONNECTOR = re.compile(r"<em>\s*(OR|AND)\s*</em>")
_INNER_CONNECTOR = re.compile(r"(and|or)(?=\s|\()")
_AT_LEAST = re.compile(r"Any\s+Course\s+EQUAL\s+or\s+GREATER\s+Than\s*:", re.IGNORECASE)
_N_OF = re.compile(r"Any\s+(\w+)\s+Courses?\s+from\s+the\s+following\s*:", re.IGNORECASE)
# A course title runs until the whitespace before a closing paren, a lowercase
# connector, an <em> connector, or the end of the string.
_TITLE_END = re.compile(r"\s+\)|\s+(?:and|or)[\s(]|\s*<em>|$")


class PrereqParseError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str  # LP, RP, AND, OR, COURSE, AT_LEAST, N_OF
    value: str = ""


@dataclass(frozen=True)
class ParsedPrereq:
    raw: str
    tree: PrereqNode | None
    ok: bool
    error: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.raw.strip()


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            tokens.append(Token("LP"))
            i += 1
            continue
        if ch == ")":
            tokens.append(Token("RP"))
            i += 1
            continue

        m = _TOP_CONNECTOR.match(text, i)
        if m:
            tokens.append(Token(m.group(1)))
            i = m.end()
            continue

        m = _AT_LEAST.match(text, i)
        if m:
            tokens.append(Token("AT_LEAST"))
            i = m.end()
            continue

        m = _N_OF.match(text, i)
        if m:
            word = m.group(1).lower()
            count = _NUMBER_WORDS.get(word) or (int(word) if word.isdigit() else None)
            if count is None:
                raise PrereqParseError(f"unknown count word {word!r}")
            tokens.append(Token("N_OF", str(count)))
            i = m.end()
            continue

        m = COURSE_RE.match(text, i)
        if m:
            tokens.append(Token("COURSE", m.group(0)))
            end = _TITLE_END.search(text, m.end())
            i = end.start() if end else n
            continue

        m = _INNER_CONNECTOR.match(text, i)
        if m:
            tokens.append(Token(m.group(1).upper()))
            i = m.end()
            continue

        snippet = text[i : i + 40]
        raise PrereqParseError(f"unexpected text at {i}: {snippet!r}")
    return tokens


class _Parser:
    """Recursive descent. `and` binds tighter than `or`, like most boolean syntax."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self, kind: str) -> Token:
        tok = self.peek()
        if tok is None or tok.kind != kind:
            got = tok.kind if tok else "end"
            raise PrereqParseError(f"expected {kind}, got {got} at token {self.pos}")
        self.pos += 1
        return tok

    def parse(self) -> PrereqNode:
        node = self.expr()
        if self.peek() is not None:
            raise PrereqParseError(f"trailing tokens from {self.pos}")
        return node

    def expr(self) -> PrereqNode:
        children = [self.term()]
        while (tok := self.peek()) is not None and tok.kind == "OR":
            self.pos += 1
            children.append(self.term())
        return _combine("any", children)

    def term(self) -> PrereqNode:
        children = [self.factor()]
        while (tok := self.peek()) is not None and tok.kind == "AND":
            self.pos += 1
            children.append(self.factor())
        return _combine("all", children)

    def factor(self) -> PrereqNode:
        tok = self.peek()
        if tok is None:
            raise PrereqParseError("unexpected end of prerequisites")
        if tok.kind == "LP":
            self.pos += 1
            node = self.expr()
            self.take("RP")
            return node
        if tok.kind == "COURSE":
            self.pos += 1
            return {"type": "course", "course": tok.value}
        if tok.kind == "AT_LEAST":
            self.pos += 1
            self.take("LP")
            course = self.take("COURSE").value
            self.take("RP")
            return {"type": "at_least", "course": course}
        if tok.kind == "N_OF":
            self.pos += 1
            options: list[PrereqNode] = []
            while (nxt := self.peek()) is not None and nxt.kind == "LP":
                self.pos += 1
                options.append(self.expr())
                self.take("RP")
            if not options:
                raise PrereqParseError("'Any N Course' with no listed courses")
            return {"type": "n_of", "n": int(tok.value), "of": _dedupe(options)}
        raise PrereqParseError(f"unexpected {tok.kind} at token {self.pos}")


def _dedupe(nodes: Iterable[PrereqNode]) -> list[PrereqNode]:
    seen: set[str] = set()
    out: list[PrereqNode] = []
    for node in nodes:
        key = json.dumps(node, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(node)
    return out


def _combine(kind: str, children: list[PrereqNode]) -> PrereqNode:
    flat: list[PrereqNode] = []
    for child in children:
        if child.get("type") == kind:
            flat.extend(child["of"])
        else:
            flat.append(child)
    flat = _dedupe(flat)
    if len(flat) == 1:
        return flat[0]
    return {"type": kind, "of": flat}


def has_mixed_top_level(raw: str) -> bool:
    """True when <em> OR </em> and <em> AND </em> both appear between groups.

    We parse these with standard precedence (AND before OR). Rutgers doesn't
    document its intent, so callers may want to flag these for review.
    """
    kinds = {m.group(1) for m in _TOP_CONNECTOR.finditer(raw)}
    return kinds == {"OR", "AND"}


def parse_prereqs(raw: str | None) -> ParsedPrereq:
    text = (raw or "").strip()
    if not text:
        return ParsedPrereq(raw="", tree=None, ok=True)
    try:
        tree = _Parser(tokenize(text)).parse()
    except PrereqParseError as exc:
        return ParsedPrereq(raw=text, tree=None, ok=False, error=str(exc))
    return ParsedPrereq(raw=text, tree=tree, ok=True)


def _split(course: str) -> tuple[str, int]:
    school, subject, number = course.split(":")
    return f"{school}:{subject}", int(number)


def is_satisfied(tree: PrereqNode | None, completed: set[str]) -> bool:
    """Whether a set of completed course strings satisfies the tree.

    An empty tree (no prerequisites) is always satisfied. This only checks
    course completion: it ignores grade minimums, placement tests, and
    "permission of instructor", which SOC notes do not encode.
    """
    if tree is None:
        return True
    kind = tree["type"]
    if kind == "course":
        return tree["course"] in completed
    if kind == "all":
        return all(is_satisfied(child, completed) for child in tree["of"])
    if kind == "any":
        return any(is_satisfied(child, completed) for child in tree["of"])
    if kind == "n_of":
        return sum(is_satisfied(child, completed) for child in tree["of"]) >= tree["n"]
    if kind == "at_least":
        prefix, floor = _split(tree["course"])
        for done in completed:
            if COURSE_RE.fullmatch(done):
                done_prefix, number = _split(done)
                if done_prefix == prefix and number >= floor:
                    return True
        return False
    raise ValueError(f"unknown prerequisite node type {kind!r}")


def courses_in(tree: PrereqNode | None) -> set[str]:
    """Every course string named anywhere in the tree."""
    if tree is None:
        return set()
    if tree["type"] in ("course", "at_least"):
        return {tree["course"]}
    out: set[str] = set()
    for child in tree["of"]:
        out |= courses_in(child)
    return out
