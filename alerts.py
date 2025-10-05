import argparse
from models import get_session
from datetime import datetime, timedelta, timezone
from tabulate import tabulate
from sqlalchemy import text
from dateutil import parser

def alert_inactive(db='sqlite:///campus_er.db', entity_id=None):
    session = get_session(db)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=12)

    if entity_id:
        # Query just one entity
        res = session.execute(
            text("SELECT entity_id, MAX(timestamp) as last_ts FROM events WHERE entity_id = :eid GROUP BY entity_id"),
            {"eid": entity_id}
        ).fetchall()
    else:
        # Query all entities
        res = session.execute(
            text("SELECT entity_id, MAX(timestamp) as last_ts FROM events GROUP BY entity_id")
        ).fetchall()

    inactive = []
    for row in res:
        entity_id, last_ts = row

        if last_ts is not None and isinstance(last_ts, str):
            try:
                last_ts = datetime.fromisoformat(last_ts)
            except Exception:
                try:
                    last_ts = parser.parse(last_ts)
                except:
                    last_ts = None

        if last_ts is not None and hasattr(last_ts, "tzinfo") and last_ts.tzinfo is not None:
            last_ts = last_ts.replace(tzinfo=None)

        if last_ts is None or last_ts < cutoff:
            status = "❌ Inactive (>12h)"
            inactive.append((entity_id, str(last_ts), status))
        else:
            status = "✅ Active (seen within 12h)"
            inactive.append((entity_id, str(last_ts), status))

    # Always print result
    print(f"Cutoff time: {cutoff.isoformat()}")
    print(tabulate(inactive, headers=['entity_id','last_seen','status']))

    return inactive

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='sqlite:///campus_er.db')
    parser.add_argument('--entity_id', help="Check only this entity ID")
    args = parser.parse_args()
    alert_inactive(args.db, args.entity_id)
