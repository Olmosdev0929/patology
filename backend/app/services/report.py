"""Printable biopsy report and slide labels (self-contained HTML, opened in the system browser).

Telegram's in-app webview cannot reliably print, so the Mini App opens these pages through a
short-lived signed link in the external browser, where "Print → Save as PDF" works everywhere.
"""
from datetime import datetime, timedelta, timezone
from html import escape

import jwt

from .. import config
from ..models import Biopsy

TOKEN_TTL = timedelta(minutes=5)

T = {
    "uz": {
        "report": "Patogistologik xulosa", "labels": "Stakan stikerlari", "patient": "Bemor", "age": "Yosh",
        "organ": "A'zo", "suspicion": "Klinik taxmin", "panel": "IHC paneli", "scoring": "Skoring", "macro": "Makroskopiya",
        "micro": "Mikroskopiya", "diagnosis": "Xulosa", "signed": "Imzo", "status": "Holat", "date": "Sana", "print": "Chop etish",
        "draft": "QORALAMA — yakunlanmagan", "lab": "Patomorfologiya laboratoriyasi",
    },
    "ru": {
        "report": "Патогистологическое заключение", "labels": "Наклейки на стёкла", "patient": "Пациент", "age": "Возраст",
        "organ": "Орган", "suspicion": "Клинический диагноз", "panel": "Панель ИГХ", "scoring": "Скоринг", "macro": "Макроскопия",
        "micro": "Микроскопия", "diagnosis": "Заключение", "signed": "Подпись", "status": "Статус", "date": "Дата", "print": "Печать",
        "draft": "ЧЕРНОВИК — не подписано", "lab": "Лаборатория патоморфологии",
    },
}

ORGANS = {
    "uz": {"breast": "Ko'krak bezi", "lung": "O'pka", "colon": "Yo'g'on ichak", "stomach": "Oshqozon", "liver": "Jigar",
           "kidney": "Buyrak", "prostate": "Prostata", "thyroid": "Qalqonsimon bez", "skin": "Teri",
           "lymph": "Limfa tugunlari", "cervix": "Bachadon bo'yni", "other": "Boshqa"},
    "ru": {"breast": "Молочная железа", "lung": "Лёгкое", "colon": "Толстая кишка", "stomach": "Желудок", "liver": "Печень",
           "kidney": "Почка", "prostate": "Простата", "thyroid": "Щитовидная железа", "skin": "Кожа",
           "lymph": "Лимфоузлы", "cervix": "Шейка матки", "other": "Другое"},
}
STATUS = {
    "uz": {"registered": "Ro'yxatda", "approved": "Tasdiqlangan", "reported": "Yakunlangan"},
    "ru": {"registered": "Зарегистрирована", "approved": "Утверждена", "reported": "Завершена"},
}

CSS = """
*{box-sizing:border-box} body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#0f172a;margin:0;padding:24px;background:#fff}
h1{font-size:20px;margin:0 0 4px} .muted{color:#64748b} .code{font:700 22px ui-monospace,Menlo,monospace;color:#0b7268}
table{border-collapse:collapse;width:100%;margin:8px 0} td,th{border:1px solid #e2e8f0;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f1f5f9;width:30%} h2{font-size:15px;margin:18px 0 6px;border-bottom:2px solid #0f8a7e;padding-bottom:2px}
.pre{white-space:pre-wrap} .draft{color:#be123c;font-weight:700;border:2px solid #be123c;padding:4px 8px;display:inline-block;margin:8px 0}
.head{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid #0f8a7e;padding-bottom:8px;margin-bottom:12px}
.labels{display:grid;grid-template-columns:repeat(auto-fill,25mm);gap:3mm}
.label{width:25mm;height:25mm;border:1px dashed #94a3b8;padding:1.5mm;display:flex;flex-direction:column;justify-content:space-between;font:9px/1.2 ui-monospace,Menlo,monospace}
.label b{font-size:10px} .label .m{font-size:12px;font-weight:700}
button{margin-top:16px;padding:10px 16px;border:0;border-radius:10px;background:#0f8a7e;color:#fff;font-weight:600}
@media print{button{display:none} body{padding:0} @page{margin:12mm}}
"""


def issue_link_token(code: str, kind: str, lang: str) -> str:
    payload = {"scope": f"{kind}:{code}", "lang": lang, "exp": datetime.now(timezone.utc) + TOKEN_TTL}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def check_link_token(token: str, code: str, kind: str) -> str | None:
    """Returns the language if the token is valid for this case and page kind."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return payload.get("lang", "uz") if payload.get("scope") == f"{kind}:{code}" else None


def _page(title: str, body: str, lang: str) -> str:
    return (f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title><style>{CSS}</style></head><body>{body}"
            f"<button onclick='window.print()'>{T[lang]['print']}</button></body></html>")


def _scoring(r: dict | None) -> str:
    if not r:
        return "—"
    parts = []
    for k in ("er", "pr"):
        if k in r:
            parts.append(f"{k.upper()}: {r[k]['percent']}% · Allred {r[k]['total']}/8 ({r[k]['category']})")
    if "her2" in r:
        parts.append(f"HER2: {r['her2']['label']} ({r['her2']['status']})")
    if "ki67" in r:
        parts.append(f"Ki-67: {r['ki67']['percent']}%")
    if r.get("subtype"):
        parts.append(f"Subtype: {r['subtype']}")
    return "<br>".join(escape(p) for p in parts)


def render_report(b: Biopsy, approver: str | None, lang: str) -> str:
    t = T.get(lang, T["uz"])
    sex = {"uz": {"M": "Erkak", "F": "Ayol"}, "ru": {"M": "Муж.", "F": "Жен."}}.get(lang, {}).get(b.patient_sex or "", "")
    rows = [
        (t["patient"], f"{b.patient_name}" + (f", {b.patient_age}" if b.patient_age is not None else "") + (f" · {sex}" if sex else "")),
        (t["organ"], ORGANS.get(lang, ORGANS["uz"]).get(b.organ, b.organ)), (t["suspicion"], b.clinical_suspicion or "—"),
        (t["panel"], ", ".join(m["name"] for m in b.selected_markers) or "—"),
    ]
    body = [
        f"<div class='head'><div><div class='muted'>{t['lab']}</div><h1>{t['report']}</h1></div>"
        f"<div style='text-align:right'><div class='code'>{escape(b.code)}</div>"
        f"<div class='muted'>{t['date']}: {b.created_at:%Y-%m-%d}</div></div></div>",
    ]
    if b.status != "reported":
        body.append(f"<div class='draft'>{t['draft']}</div>")
    body.append("<table>" + "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows) + "</table>")
    body.append(f"<h2>{t['scoring']}</h2><div>{_scoring(b.scoring_result)}</div>")
    for key, title in (("macro_text", t["macro"]), ("micro_text", t["micro"]), ("diagnosis", t["diagnosis"])):
        body.append(f"<h2>{title}</h2><div class='pre'>{escape(getattr(b, key) or '—')}</div>")
    body.append(f"<p style='margin-top:28px'>{t['signed']}: <b>{escape(approver or '______________')}</b>"
                f" &nbsp; {t['status']}: {escape(STATUS.get(lang, STATUS['uz']).get(b.status, b.status))}</p>")
    return _page(f"{b.code} — {t['report']}", "".join(body), lang)


def render_labels(b: Biopsy, lang: str) -> str:
    t = T.get(lang, T["uz"])
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slides = [("H&E", "")] + [(m["name"], m.get("source", "")) for m in b.selected_markers]
    cells = "".join(
        f"<div class='label'><b>{escape(b.code)}</b><span class='m'>{escape(name)}</span><span>{day}</span></div>"
        for name, _ in slides
    )
    return _page(f"{b.code} — {t['labels']}", f"<h1>{t['labels']} · <span class='code'>{escape(b.code)}</span></h1>"
                 f"<p class='muted'>25 × 25 mm</p><div class='labels'>{cells}</div>", lang)
