import pandas as pd
import argparse, json
from models import init_db, get_session, Entity, Event, FaceEmbedding, Note
from datetime import datetime
from dateutil import parser

# Canonical 8 locations from card swipes
CANONICAL_LOCATIONS = {
    "AUDITORIUM": "AUDITORIUM",
    "ADMIN_LOBBY": "ADMIN_LOBBY",
    "LIB_ENT": "LIB_ENT",
    "GYM": "GYM",
    "HOSTEL_GATE": "HOSTEL_GATE",
    "CAF_01": "CAF_01",
    "LAB_305": "LAB_305",
    "LAB_101": "LAB_101",
}

def normalize_location(raw):
    """Map raw AP IDs / room IDs to the 8 canonical locations"""
    if pd.isna(raw):
        return None
    s = str(raw).upper()

    # Map WiFi AP IDs
    if s.startswith("AP_LIB"):
        return "LIB_ENT"
    if s.startswith("AP_CAF"):
        return "CAF_01"
    if s.startswith("AP_HOSTEL"):
        return "HOSTEL_GATE"
    if s.startswith("AP_ADMIN"):
        return "ADMIN_LOBBY"
    if s.startswith("AP_AUD"):
        return "AUDITORIUM"
    # Direct matches
    if s in CANONICAL_LOCATIONS:
        return s

    # Special cases
    if "AUDITORIUM" in s:
        return "AUDITORIUM"
    if "GYM" in s:
        return "GYM"
    if "LAB" in s or "ENG" in s:
        return "LAB_101"  # all labs/eng mapped to LAB_101 for now

    return s  # fallback, unmapped values

def try_parse_time(val):
    if val is None or str(val).strip() == "":
        return None
    val = str(val).strip()
    try:
        return parser.parse(val)  # flexible parse
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except Exception:
                continue
    print(f"⚠️ Could not parse timestamp: {val}")
    return None

def load_profiles(csv_path, db):
    init_db(db)
    session = get_session(db)
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        ent_id = str(row.get('entity_id') or '')
        if not ent_id:
            continue
        e = Entity(
            entity_id=ent_id,
            student_id=row.get('student_id'),
            staff_id=row.get('staff_id'),
            card_id=row.get('card_id'),
            device_hash=row.get('device_hash'),
            face_id=row.get('face_id'),
            name=row.get('name'),
            role=row.get('role'),
            email=row.get('email'),
            metadata=row.to_dict()
        )
        session.merge(e)
    session.commit()
    print('Profiles ingested.')

def resolve_entity_by_alts(session, card=None, device=None, face=None):
    if card:
        r = session.query(Entity).filter(Entity.card_id==str(card)).first()
        if r: return r.entity_id
    if device:
        r = session.query(Entity).filter(Entity.device_hash==str(device)).first()
        if r: return r.entity_id
    if face:
        r = session.query(Entity).filter(Entity.face_id==str(face)).first()
        if r: return r.entity_id
    return None

def load_events(csv_path, db, source, entity_col=None, location_col=None, timestamp_col=None):
    init_db(db)
    session = get_session(db)
    df = pd.read_csv(csv_path)
    count = 0
    skipped = 0

    for _, row in df.iterrows():
        # ✅ Only keep attended lab bookings
        if source == "lab_booking":
            attended = row.get("attended")
            if attended is None:
                skipped += 1
                continue
            attended_str = str(attended).strip().lower()
            if attended_str not in ["1", "true", "yes", "y"]:
                skipped += 1
                continue

        # Try multiple timestamp sources
        val = None
        if timestamp_col and timestamp_col in row and pd.notna(row.get(timestamp_col)):
            val = row.get(timestamp_col)
        elif "timestamp" in row and pd.notna(row.get("timestamp")):
            val = row.get("timestamp")
        elif "time" in row and pd.notna(row.get("time")):
            val = row.get("time")
        elif "start_time" in row and pd.notna(row.get("start_time")):
            val = row.get("start_time")

        ts = try_parse_time(val)

        raw_id = None
        resolved = None
        if entity_col and entity_col in row and pd.notna(row.get(entity_col)):
            val = row.get(entity_col)
            resolved = resolve_entity_by_alts(session, card=val, device=val, face=val)
            raw_id = str(val)

        ev = Event(
            entity_id=resolved,
            raw_id=raw_id,
            source=source,
            location=normalize_location(row.get(location_col)) if location_col else None,
            timestamp=ts,
            raw=row.to_dict()
        )
        session.add(ev)
        count += 1
        if count % 1000 == 0:
            session.commit()

    session.commit()
    print(f'Ingested {count} events from {csv_path}')
    if skipped:
        print(f'⚠️ Skipped {skipped} unattended lab bookings')

def load_notes(csv_path, db):
    init_db(db)
    session = get_session(db)
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        ts = try_parse_time(row.get('timestamp'))
        note = Note(
            note_id=row.get('note_id'),
            entity_id=row.get('entity_id'),
            timestamp=ts,
            category=row.get('category'),
            text=row.get('text')
        )
        session.add(note)
    session.commit()
    print('Notes ingested.')

def load_embeddings(csv_path, db):
    init_db(db)
    session = get_session(db)
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        ts = try_parse_time(row.get('timestamp'))
        emb = FaceEmbedding(
            face_id=row.get('face_id'),
            entity_id=None,
            camera_id=None,
            timestamp=ts,
            vector=json.loads(row.get('embeddings')) if 'embeddings' in row and pd.notna(row.get('embeddings')) else None
        )
        session.add(emb)
    session.commit()
    print('Embeddings ingested.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--table', default='events', choices=['events','entities','notes','embeddings'])
    parser.add_argument('--entity_col')
    parser.add_argument('--location_col')
    parser.add_argument('--timestamp_col')
    parser.add_argument('--db', default='sqlite:///campus_er.db')
    args = parser.parse_args()
    if args.table == 'entities':
        load_profiles(args.csv, args.db)
    elif args.table == 'events':
        load_events(args.csv, args.db, args.source, args.entity_col, args.location_col, args.timestamp_col)
    elif args.table == 'notes':
        load_notes(args.csv, args.db)
    elif args.table == 'embeddings':
        load_embeddings(args.csv, args.db)
