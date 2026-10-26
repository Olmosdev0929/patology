from datetime import date

import pytest

from app.services import scoring, sm2


@pytest.mark.parametrize("percent,ps", [(0, 0), (0.5, 1), (1, 2), (10, 2), (11, 3), (33, 3), (34, 4), (66, 4), (67, 5), (100, 5)])
def test_allred_proportion(percent, ps):
    assert scoring.allred_proportion_score(percent) == ps


def test_allred_total_and_category():
    r = scoring.allred(40, 2)
    assert (r["total"], r["allred_positive"], r["category"]) == (6, True, "positive")
    assert scoring.allred(5, 1)["category"] == "low_positive"
    assert scoring.allred(0, 0)["total"] == 0
    # <1% is ASCO/CAP negative even though the Allred sum reaches 3
    r = scoring.allred(0.5, 2)
    assert r["total"] == 3 and r["category"] == "negative"
    with pytest.raises(ValueError):
        scoring.allred(120, 1)


def test_her2():
    assert scoring.her2(3)["status"] == "positive"
    assert scoring.her2(2) | {} == {"score": 2, "label": "2+", "status": "equivocal", "action": "reflex_ish", "ish_amplified": None}
    assert scoring.her2(2, ish_amplified=True)["status"] == "positive"
    assert scoring.her2(2, ish_amplified=False)["status"] == "low"
    assert scoring.her2(1)["status"] == "low"
    assert scoring.her2(pattern="faint_incomplete_le10")["status"] == "ultralow"
    assert scoring.her2(pattern="none")["status"] == "zero"
    with pytest.raises(ValueError):
        scoring.her2(pattern="bogus")


@pytest.mark.parametrize("er,pr,her2,ki,expected", [
    (90, 50, "zero", 10, "luminal_a"),
    (90, 10, "low", 10, "luminal_b_her2_neg"),     # PR < 20%
    (90, 50, "zero", 35, "luminal_b_her2_neg"),    # high Ki-67
    (90, 50, "positive", 30, "luminal_b_her2_pos"),
    (0, 0, "positive", 40, "her2_enriched"),
    (0, 0, "low", 60, "triple_negative"),
    (90, 50, "equivocal", 10, "pending_her2"),
])
def test_breast_subtype(er, pr, her2, ki, expected):
    assert scoring.breast_subtype(scoring.SubtypeInput(er, pr, her2, ki))["subtype"] == expected


def test_compute_full_panel():
    r = scoring.compute({"er": {"percent": 80, "intensity": 3}, "pr": {"percent": 60, "intensity": 2},
                         "her2": {"score": 1}, "ki67": 12})
    assert r["er"]["total"] == 8 and r["pr"]["total"] == 6 and r["subtype"] == "luminal_a"


def test_sm2_sequence():
    d0 = date(2026, 1, 1)
    s, nxt = sm2.review(sm2.CardState(), "good", d0)
    assert (s.interval, s.reps, nxt) == (1, 1, date(2026, 1, 2))
    s, _ = sm2.review(s, "good", d0)
    assert s.interval == 6
    s, _ = sm2.review(s, "good", d0)
    assert s.interval == round(6 * s.easiness)
    ef_before = s.easiness
    s, nxt = sm2.review(s, "again", d0)
    assert (s.interval, s.reps, s.lapses) == (1, 0, 1) and s.easiness < ef_before
    hard, _ = sm2.review(sm2.CardState(), "hard")
    assert hard.easiness < 2.5
    easy, _ = sm2.review(sm2.CardState(interval=6, reps=2), "easy")
    assert easy.easiness > 2.5 and easy.interval > 6 * 2.5


def test_sm2_easiness_floor():
    s = sm2.CardState(easiness=1.3)
    for _ in range(5):
        s, _ = sm2.review(s, "again")
    assert s.easiness == sm2.MIN_EF
