import argparse, time
import pandas as pd
from collections import defaultdict
from models import init_db, get_session, Transition
from datetime import datetime
import sqlalchemy

def train_markov(db='sqlite:///campus_er.db', min_support=1):
    init_db(db)
    engine = sqlalchemy.create_engine(db, connect_args={'check_same_thread': False} if db.startswith('sqlite') else {})
    df = pd.read_sql('SELECT entity_id, location, timestamp FROM events ORDER BY entity_id, timestamp',
                     engine, parse_dates=['timestamp'])
    counts = defaultdict(lambda: defaultdict(int))
    for ent, g in df.groupby('entity_id'):
        locs = g['location'].tolist()
        for a,b in zip(locs, locs[1:]):
            if a is None or b is None:
                continue
            counts[a][b] += 1
    session = get_session(db)
    session.query(Transition).delete()
    session.commit()
    rows = 0
    for a, to_dict in counts.items():
        total = sum(to_dict.values())
        for b, c in to_dict.items():
            if c >= min_support:
                prob = c / total
                t = Transition(from_loc=a, to_loc=b, count=int(c), prob=float(prob), last_updated=datetime.utcnow())
                session.add(t)
                rows += 1
    session.commit()
    print(f'Saved {rows} transitions.')
    return rows

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='sqlite:///campus_er.db')
    parser.add_argument('--min_support', type=int, default=1)
    args = parser.parse_args()
    start = time.time()
    train_markov(args.db, args.min_support)
    print('Training time (s):', time.time()-start)
