import argparse
from models import get_session, Event, Entity
from dateutil import parser as dtparser
from tabulate import tabulate

def timeline(entity_id, db='sqlite:///campus_er.db', start=None, end=None, out_file=None):
    session = get_session(db)

    # Fetch entity info
    ent = session.query(Entity).filter(Entity.entity_id==str(entity_id)).first()

    # Build query
    q = session.query(Event).filter(Event.entity_id==str(entity_id))
    if start:
        q = q.filter(Event.timestamp >= dtparser.parse(start))
    if end:
        q = q.filter(Event.timestamp <= dtparser.parse(end))
    q = q.order_by(Event.timestamp)
    rows = q.all()

    # === Tabular Record ===
    table_out = []
    for r in rows:
        table_out.append((
            r.timestamp.isoformat() if r.timestamp else None,
            r.source,
            r.location,
            r.raw
        ))

    table_str = tabulate(table_out, headers=['timestamp','source','location','raw'])
    print("=== Tabular Record ===")
    print(table_str)

    # === Narrative Summary ===
    summary_lines = []
    if ent:
        summary_lines.append(f"Timeline for {ent.role or 'Entity'} {ent.name or ent.entity_id}:")
    else:
        summary_lines.append(f"Timeline for entity {entity_id}:")

    for r in rows:
        ts_str = r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "Unknown time"
        summary_lines.append(f"- At {ts_str}, seen at {r.location} (via {r.source}).")

    summary_str = "\n".join(summary_lines)

    print("\n=== Narrative Summary ===")
    print(summary_str)

    # Optionally save to file
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("=== Tabular Record ===\n")
            f.write(table_str + "\n\n")
            f.write("=== Narrative Summary ===\n")
            f.write(summary_str)
        print(f"\n✅ Timeline exported to {out_file}")

    return rows

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--entity_id', required=True, help="Entity ID to show timeline for")
    parser.add_argument('--db', default='sqlite:///campus_er.db', help="Path to database")
    parser.add_argument('--start', help="Start time (YYYY-MM-DD or ISO timestamp)")
    parser.add_argument('--end', help="End time (YYYY-MM-DD or ISO timestamp)")
    parser.add_argument('--out', help="Optional file path to save timeline output")
    args = parser.parse_args()

    timeline(args.entity_id, args.db, args.start, args.end, args.out)
