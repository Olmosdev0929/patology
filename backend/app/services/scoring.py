"""IHC scoring calculators: Allred (ER/PR), HER2 (ASCO/CAP), Ki-67 and breast surrogate subtypes.

References:
- Allred DC et al., Mod Pathol 1998 (Allred score).
- ASCO/CAP ER/PgR guideline update 2020 (≥1% = positive; 1–10% = "low positive").
- ASCO/CAP HER2 guideline update 2018, affirmed 2023 (HER2-low / ultralow categories).
- St Gallen 2013 surrogate definitions (Ki-67 cut-off is lab-specific; 20% default here).
"""
from dataclasses import dataclass


def allred_proportion_score(percent: float) -> int:
    """Map % positive nuclei to the Allred proportion score (0–5)."""
    if percent <= 0:
        return 0
    if percent < 1:
        return 1
    if percent <= 10:
        return 2
    if percent <= 33:
        return 3
    if percent <= 66:
        return 4
    return 5


def allred(percent: float, intensity: int) -> dict:
    """Allred total score with ASCO/CAP category.

    intensity: 0 none, 1 weak, 2 moderate, 3 strong.
    """
    if not 0 <= percent <= 100:
        raise ValueError("percent must be 0..100")
    if intensity not in (0, 1, 2, 3):
        raise ValueError("intensity must be 0..3")
    ps = allred_proportion_score(percent)
    total = ps + intensity if ps else 0
    if percent < 1 or intensity == 0:
        category = "negative"
    elif percent <= 10:
        category = "low_positive"
    else:
        category = "positive"
    return {
        "percent": percent,
        "proportion_score": ps,
        "intensity_score": intensity,
        "total": total,
        "allred_positive": total >= 3,
        "category": category,
    }


# HER2 IHC patterns -> score (ASCO/CAP 2018/2023, breast)
HER2_PATTERNS = {
    "none": 0,                       # no staining observed
    "faint_incomplete_le10": 0,      # incomplete, faint/barely perceptible in ≤10% → "ultralow"
    "faint_incomplete_gt10": 1,      # incomplete, faint/barely perceptible in >10%
    "weak_moderate_complete": 2,     # weak–moderate complete membrane in >10%
    "intense_complete_le10": 2,      # complete intense membrane in ≤10%
    "intense_complete_gt10": 3,      # complete intense circumferential membrane in >10%
}


def her2(score: int | None = None, pattern: str | None = None, ish_amplified: bool | None = None) -> dict:
    """HER2 interpretation from an IHC score (0–3) or a staining pattern.

    ish_amplified: result of reflex ISH for 2+ (None if not done).
    """
    if pattern is not None:
        if pattern not in HER2_PATTERNS:
            raise ValueError(f"unknown HER2 pattern: {pattern}")
        score = HER2_PATTERNS[pattern]
    if score not in (0, 1, 2, 3):
        raise ValueError("HER2 score must be 0..3")

    action = None
    if score == 3:
        status = "positive"
    elif score == 2:
        if ish_amplified is None:
            status, action = "equivocal", "reflex_ish"
        else:
            status = "positive" if ish_amplified else "low"
    elif score == 1:
        status = "low"
    else:
        status = "ultralow" if pattern == "faint_incomplete_le10" else "zero"
    return {"score": score, "label": f"{score}+" if score else "0", "status": status, "action": action, "ish_amplified": ish_amplified}


@dataclass
class SubtypeInput:
    er_percent: float
    pr_percent: float
    her2_status: str      # positive | equivocal | low | ultralow | zero
    ki67_percent: float
    ki67_cutoff: float = 20.0


def ki67_band(percent: float, cutoff: float = 20.0) -> str:
    if not 0 <= percent <= 100:
        raise ValueError("Ki-67 must be 0..100")
    return "high" if percent >= cutoff else "low"


def breast_subtype(x: SubtypeInput) -> dict:
    """St Gallen-style IHC surrogate of intrinsic molecular subtypes."""
    if x.her2_status == "equivocal":
        return {"subtype": "pending_her2", "ki67_band": ki67_band(x.ki67_percent, x.ki67_cutoff)}
    hr_pos = x.er_percent >= 1 or x.pr_percent >= 1
    her2_pos = x.her2_status == "positive"
    band = ki67_band(x.ki67_percent, x.ki67_cutoff)
    if hr_pos and her2_pos:
        subtype = "luminal_b_her2_pos"
    elif hr_pos:
        # Luminal A requires ER+, PR ≥20% and low Ki-67.
        subtype = "luminal_a" if (x.er_percent >= 1 and x.pr_percent >= 20 and band == "low") else "luminal_b_her2_neg"
    elif her2_pos:
        subtype = "her2_enriched"
    else:
        subtype = "triple_negative"
    return {"subtype": subtype, "ki67_band": band, "ki67_cutoff": x.ki67_cutoff}


def compute(payload: dict) -> dict:
    """Compute a full scoring result from the PUT /scoring body."""
    result: dict = {}
    if er := payload.get("er"):
        result["er"] = allred(er["percent"], er["intensity"])
    if pr := payload.get("pr"):
        result["pr"] = allred(pr["percent"], pr["intensity"])
    if h := payload.get("her2"):
        result["her2"] = her2(h.get("score"), h.get("pattern"), h.get("ish_amplified"))
    if (ki := payload.get("ki67")) is not None:
        cutoff = payload.get("ki67_cutoff", 20.0)
        result["ki67"] = {"percent": ki, "band": ki67_band(ki, cutoff), "cutoff": cutoff}
    if all(k in result for k in ("er", "pr", "her2", "ki67")):
        result["subtype"] = breast_subtype(SubtypeInput(
            er_percent=result["er"]["percent"] if result["er"]["intensity_score"] else 0,
            pr_percent=result["pr"]["percent"] if result["pr"]["intensity_score"] else 0,
            her2_status=result["her2"]["status"],
            ki67_percent=result["ki67"]["percent"],
            ki67_cutoff=result["ki67"]["cutoff"],
        ))["subtype"]
    return result
