import json
from pathlib import Path

import pytest

from advisor.soc.prereqs import (
    courses_in,
    has_mixed_top_level,
    is_satisfied,
    parse_prereqs,
)

FIXTURE = Path(__file__).parent / "fixtures" / "soc_sample.json"


def _raw(course_string: str) -> str:
    for record in json.loads(FIXTURE.read_text()):
        if record["courseString"] == course_string:
            return str(record["preReqNotes"])
    raise KeyError(course_string)


def test_empty_prereqs_are_ok_and_always_satisfied():
    parsed = parse_prereqs("")
    assert parsed.ok and parsed.tree is None and parsed.is_empty
    assert is_satisfied(parsed.tree, set())


def test_single_course():
    parsed = parse_prereqs(_raw("01:198:112"))
    assert parsed.tree == {"type": "course", "course": "01:198:111"}


def test_at_least_form():
    parsed = parse_prereqs(_raw("01:198:111"))
    assert parsed.tree == {"type": "at_least", "course": "01:640:112"}
    assert is_satisfied(parsed.tree, {"01:640:151"})
    assert is_satisfied(parsed.tree, {"01:640:112"})
    assert not is_satisfied(parsed.tree, {"01:640:111"})
    # Different subject with a higher number does not count.
    assert not is_satisfied(parsed.tree, {"01:750:193"})


def test_nested_groups_for_discrete_ii():
    tree = parse_prereqs(_raw("01:198:206")).tree
    assert is_satisfied(tree, {"01:198:205", "01:640:152"})
    assert is_satisfied(tree, {"14:332:312", "01:640:152"})
    assert not is_satisfied(tree, {"01:198:205"})  # missing calc II
    assert not is_satisfied(tree, {"01:640:152"})  # missing discrete I


def test_algorithms_requires_data_structures_and_discrete_ii_or_probability():
    tree = parse_prereqs(_raw("01:198:344")).tree
    assert is_satisfied(tree, {"01:198:112", "01:198:206"})
    assert is_satisfied(tree, {"14:332:351", "01:198:206"})
    assert not is_satisfied(tree, {"01:198:111", "01:198:206"})
    assert {"01:198:112", "01:198:206"} <= courses_in(tree)


def test_titles_with_parentheses_and_uppercase_and():
    raw = (
        "(19:913:598 CLINICAL SOCIAL WORK (CSW) SPECIALIZATION )<em> OR </em>"
        "(01:730:101 LOGIC, REASONING, AND PERSUASION )"
    )
    parsed = parse_prereqs(raw)
    assert parsed.ok, parsed.error
    assert courses_in(parsed.tree) == {"19:913:598", "01:730:101"}
    assert parsed.tree is not None and parsed.tree["type"] == "any"


def test_n_of_form():
    raw = (
        "Any Two Course from the following: (01:615:305 SYNTAX )    "
        "(01:615:315 PHONOLOGY )    (01:615:325 SEMANTICS )"
    )
    tree = parse_prereqs(raw).tree
    assert tree is not None and tree["type"] == "n_of" and tree["n"] == 2
    assert is_satisfied(tree, {"01:615:305", "01:615:325"})
    assert not is_satisfied(tree, {"01:615:305"})


def test_duplicate_children_are_removed():
    tree = parse_prereqs("(01:198:205 A  and 01:640:152 B  and 01:640:152 B )").tree
    assert tree == {
        "type": "all",
        "of": [
            {"type": "course", "course": "01:198:205"},
            {"type": "course", "course": "01:640:152"},
        ],
    }


def test_and_binds_tighter_than_or():
    tree = parse_prereqs("(01:000:001 )<em> OR </em>(01:000:002 )<em> AND </em>(01:000:003 )").tree
    assert is_satisfied(tree, {"01:000:001"})
    assert not is_satisfied(tree, {"01:000:002"})
    assert has_mixed_top_level("(01:000:001 )<em> OR </em>(01:000:002 )<em> AND </em>(01:000:003 )")


@pytest.mark.parametrize(
    "raw",
    [
        "TWO Course Within the Subject Area:",
        "(01:198:111 INTRO",  # unbalanced
        "(01:198:111 ) and",  # dangling connector
        "Any Nine Hundred Course from the following: (01:198:111 )",
    ],
)
def test_unparseable_text_is_flagged_not_guessed(raw):
    parsed = parse_prereqs(raw)
    assert not parsed.ok
    assert parsed.tree is None
    assert parsed.error


def test_every_fixture_prereq_parses_except_known_manual_case():
    failures = []
    for record in json.loads(FIXTURE.read_text()):
        parsed = parse_prereqs(record["preReqNotes"])
        if not parsed.ok:
            failures.append(record["courseString"])
    assert failures == ["01:730:295"]
