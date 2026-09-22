import json

from src.core.database.connection import get_web_session
from src.core.models.base_models import Setting

DEFAULT_CONTRACT_TYPES = [
    ("reserve", "احتياط"),
    ("seasonal", "موسمي"),
    ("public_transport", "ركوبة عامة"),
    ("rent_to_own", "ايجار لغرض التمليك"),
]

DEFAULT_ACTIVITY_TYPES = [
    ("large_bus", "باص كبير"),
    ("small_bus", "باص صغير"),
    ("public_transport", "ركوبة"),
    ("no_driver", "بدون سائق"),
]

CONTRACT_TYPE_LABELS = {v: l for v, l in DEFAULT_CONTRACT_TYPES}
DRIVER_CONTRACT_TYPE_LABELS = CONTRACT_TYPE_LABELS
DRIVER_CONTRACT_TYPES = DEFAULT_CONTRACT_TYPES

_SETTINGS_KEYS = {
    "contract": "driver_contract_types",
    "activity": "driver_activity_types",
}


def _pairs_from_raw(raw, defaults):
    if not raw:
        return list(defaults)
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return list(defaults)
    pairs = []
    for item in data:
        if isinstance(item, dict):
            value = str(item.get("value", "")).strip()
            label = str(item.get("label", "")).strip()
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            value = str(item[0]).strip()
            label = str(item[1]).strip()
        else:
            continue
        if value and label:
            pairs.append((value, label))
    return pairs or list(defaults)


def _save_pairs(session, key, pairs):
    payload = json.dumps([{"value": v, "label": l} for v, l in pairs], ensure_ascii=False)
    row = session.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = payload
    else:
        session.add(Setting(key=key, value=payload, value_type="json", category="contract_types"))
    session.commit()


def get_type_list(kind, session=None):
    key = _SETTINGS_KEYS.get(kind)
    if not key:
        return list(DEFAULT_CONTRACT_TYPES)
    defaults = DEFAULT_ACTIVITY_TYPES if kind == "activity" else DEFAULT_CONTRACT_TYPES
    own_session = session is None
    if own_session:
        session = get_web_session()
    try:
        row = session.query(Setting).filter(Setting.key == key).first()
        pairs = _pairs_from_raw(row.value if row else None, defaults)
        if not row:
            _save_pairs(session, key, pairs)
        return pairs
    finally:
        if own_session:
            session.commit()


def get_contract_types(session=None):
    return get_type_list("contract", session=session)


def get_activity_types(session=None):
    return get_type_list("activity", session=session)


def add_type(kind, label, value=None, session=None):
    label = (label or "").strip()
    if not label:
        return False, "الاسم مطلوب"
    key = _SETTINGS_KEYS.get(kind)
    if not key:
        return False, "نوع القائمة غير صحيح"
    value = (value or label).strip()
    own_session = session is None
    if own_session:
        session = get_web_session()
    try:
        defaults = DEFAULT_ACTIVITY_TYPES if kind == "activity" else DEFAULT_CONTRACT_TYPES
        row = session.query(Setting).filter(Setting.key == key).first()
        pairs = _pairs_from_raw(row.value if row else None, defaults)
        if any(v == value or l == label for v, l in pairs):
            return False, "القيمة موجودة مسبقاً"
        pairs.append((value, label))
        _save_pairs(session, key, pairs)
        return True, "تمت الإضافة بنجاح"
    finally:
        if own_session:
            session.commit()


def delete_type(kind, value, session=None):
    value = (value or "").strip()
    if not value:
        return False, "القيمة مطلوبة"
    key = _SETTINGS_KEYS.get(kind)
    if not key:
        return False, "نوع القائمة غير صحيح"
    own_session = session is None
    if own_session:
        session = get_web_session()
    try:
        defaults = DEFAULT_ACTIVITY_TYPES if kind == "activity" else DEFAULT_CONTRACT_TYPES
        row = session.query(Setting).filter(Setting.key == key).first()
        pairs = _pairs_from_raw(row.value if row else None, defaults)
        remaining = [(v, l) for v, l in pairs if v != value]
        if len(remaining) == len(pairs):
            return False, "القيمة غير موجودة"
        _save_pairs(session, key, remaining)
        return True, "تم الحذف بنجاح"
    finally:
        if own_session:
            session.commit()


def labels_for(kind=None, session=None):
    if kind:
        return [l for _, l in get_type_list(kind, session=session)]
    return [l for _, l in get_contract_types(session=session)]
