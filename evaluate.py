import argparse
import pandas as pd
from dateutil import parser
from collections import defaultdict, Counter
from models import get_engine

def build_test_transitions(events_df):
    pairs = []
    for ent, g in events_df.groupby('entity_id'):
        g = g.sort_values('timestamp')
        locs = g['location'].tolist()
        for a,b in zip(locs, locs[1:]):
            pairs.append((a,b))
    return pairs

def load_predictions_from_db(engine):
    df = pd.read_sql('SELECT from_loc,to_loc,prob,count FROM transitions', engine)
    preds = defaultdict(list)
    for _, r in df.iterrows():
        preds[r['from_loc']].append((r['to_loc'], float(r['prob']), int(r['count'])))
    for k in preds:
        preds[k].sort(key=lambda x: -x[1])
    return preds

def most_frequent_baseline(train_df):
    counts = defaultdict(Counter)
    for ent, g in train_df.groupby('entity_id'):
        g = g.sort_values('timestamp')
        locs = g['location'].tolist()
        for a,b in zip(locs, locs[1:]):
            counts[a][b] += 1
    top = {}
    global_counter = Counter()
    for a, ctr in counts.items():
        top[a] = ctr.most_common(1)[0][0]
        global_counter.update(ctr)
    global_top = global_counter.most_common(1)[0][0] if len(global_counter)>0 else None
    return top, global_top

def evaluate(pairs, preds, baseline_map, global_top, top_k=5):
    N = len(pairs)
    hits = 0
    rr_sum = 0.0
    unseen_from = 0
    for (a,b) in pairs:
        if a not in preds:
            unseen_from += 1
            candidates = [baseline_map.get(a, global_top)]
        else:
            candidates = [p[0] for p in preds[a][:top_k]]
        if b in candidates:
            hits += 1
            rank = candidates.index(b) + 1
            rr_sum += 1.0 / rank
    return {"N":N, "Hit@K": hits / N if N else 0.0, "MRR": rr_sum / N if N else 0.0, "unseen_from_count": unseen_from}

def main(db, tcut, top_k, min_support):
    engine = get_engine(db)
    conn = engine.connect()
    events = pd.read_sql('SELECT entity_id,location,timestamp FROM events', conn, parse_dates=['timestamp'])
    tcut_dt = parser.parse(tcut)
    train_df = events[events['timestamp'] < tcut_dt].copy()
    test_df = events[events['timestamp'] >= tcut_dt].copy()
    print(f'Total events: {len(events)}, train: {len(train_df)}, test: {len(test_df)}')
    test_pairs = build_test_transitions(test_df)
    preds = load_predictions_from_db(engine)
    baseline_map, global_top = most_frequent_baseline(train_df)
    res = evaluate(test_pairs, preds, baseline_map, global_top, top_k=top_k)
    print('Model evaluation (top_k=%d):' % top_k)
    for k,v in res.items():
        print('  %s: %s' % (k, v))
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='sqlite:///campus_er.db')
    parser.add_argument('--tcut', required=True)
    parser.add_argument('--top_k', type=int, default=5)
    parser.add_argument('--min_support', type=int, default=1)
    args = parser.parse_args()
    main(args.db, args.tcut, args.top_k, args.min_support)
