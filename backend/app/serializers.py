"""Model -> JSON-friendly dict converters shared by routers and the bot."""
from .models import AnkiCard, Biopsy, Disease, Image, IgxLot, IgxMarker, Organ, Role, User
from .services.inventory import days_to_expiry, status_tags


def user_out(u: User) -> dict:
    return {
        "id": u.id, "telegram_id": u.telegram_id, "name": u.name, "username": u.username, "role": u.role,
        "specialty": u.specialty, "cases_done": u.cases_done, "markers_saved": u.markers_saved,
        "is_active": u.is_active, "language": u.language,
    }


def lot_out(lot: IgxLot) -> dict:
    return {"id": lot.id, "lot_number": lot.lot_number, "expiry_date": lot.expiry_date.isoformat(),
            "quantity": lot.quantity, "received_quantity": lot.received_quantity}


def marker_out(m: IgxMarker, with_lots: bool = False) -> dict:
    out = {
        "id": m.id, "name": m.name, "clone": m.clone, "vendor": m.vendor, "organ": m.organ,
        "localization": m.localization, "description": m.description, "tandem_with": m.tandem_with,
        "reason": m.reason, "lab_passport": m.lab_passport, "stock": m.stock,
        "expiry_date": m.expiry_date.isoformat() if m.expiry_date else None,
        "days_to_expiry": days_to_expiry(m), "used_30d": m.used_30d, "is_custom": m.is_custom,
        "passport_verified": m.passport_verified_at is not None,
        "passport_verified_at": m.passport_verified_at.isoformat() if m.passport_verified_at else None,
        "tags": status_tags(m),
    }
    if with_lots:
        out["lots"] = [lot_out(lot) for lot in m.lots]
    return out


def biopsy_out(b: Biopsy, viewer: User | None = None) -> dict:
    out = {
        "id": b.id, "code": b.code, "patient_name": b.patient_name, "patient_age": b.patient_age,
        "patient_sex": b.patient_sex, "organ": b.organ, "clinical_suspicion": b.clinical_suspicion,
        "initial_tests": b.initial_tests, "status": b.status, "selected_markers": b.selected_markers,
        "macro_text": b.macro_text, "micro_text": b.micro_text, "diagnosis": b.diagnosis,
        "scoring_result": b.scoring_result, "consilium_open": b.consilium_open,
        "consilium_comments": b.consilium_comments, "created_by": b.created_by, "approved_by": b.approved_by,
        "approved_at": b.approved_at.isoformat() if b.approved_at else None,
        "created_at": b.created_at.isoformat(), "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }
    if viewer and viewer.role == Role.TECHNICIAN:
        # Technicians need the slide work-list, not the patient's identity.
        out["patient_name"] = mask_name(b.patient_name)
    return out


def mask_name(name: str) -> str:
    return " ".join(p[0] + "." for p in name.split() if p) or "—"


def organ_out(o: Organ, disease_count: int | None = None) -> dict:
    out = {"id": o.id, "slug": o.slug, "name": o.name, "icon": o.icon}
    if disease_count is not None:
        out["disease_count"] = disease_count
    return out


def disease_out(d: Disease, full: bool = True) -> dict:
    out = {"id": d.id, "slug": d.slug, "name": d.name, "name_en": d.name_en, "icd10": d.icd10}
    if full:
        out |= {"sections": d.sections, "markers": d.markers, "refs": d.refs,
                "organ": organ_out(d.organ) if d.organ else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None}
    return out


def image_out(i: Image, disease: Disease | None = None) -> dict:
    out = {
        "id": i.id, "kind": i.kind, "stain": i.stain, "caption": i.caption, "description": i.description or {},
        "credit": i.credit, "pins": i.pins, "disease_id": i.disease_id, "biopsy_id": i.biopsy_id,
        "url": f"/api/images/{i.id}/file", "created_at": i.created_at.isoformat(),
    }
    if disease is not None:
        out["disease"] = {"slug": disease.slug, "name": disease.name}
    return out


def card_out(c: AnkiCard) -> dict:
    return {
        "id": c.id, "deck": c.deck, "front_uz": c.front_uz, "front_ru": c.front_ru, "back_uz": c.back_uz,
        "back_ru": c.back_ru, "front_en": c.front_en, "sentence_id": c.sentence_id, "interval": c.interval,
        "reps": c.reps, "easiness": c.easiness, "lapses": c.lapses, "next_review": c.next_review.isoformat(),
    }
