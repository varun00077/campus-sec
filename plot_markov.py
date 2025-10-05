import argparse
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from models import get_engine

def plot_markov(db='sqlite:///campus_er.db', out='markov_chain.png'):
    engine = get_engine(db)
    df = pd.read_sql('SELECT from_loc,to_loc,prob FROM transitions', engine)
    if df.empty:
        print("No transitions found. Did you run train_markov.py?")
        return
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(row['from_loc'], row['to_loc'], weight=row['prob'], label=f"{row['prob']:.2f}")
    pos = nx.circular_layout(G)   # circular works well for ~8 locations
    plt.figure(figsize=(10,8))
    nx.draw(G, pos, with_labels=True, node_color="lightblue", node_size=2000, arrowsize=20, font_size=10)
    labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=9)
    plt.title("Markov Chain of Campus Movements")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out)
    print(f"Saved Markov chain visualization to {out}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='sqlite:///campus_er.db')
    parser.add_argument('--out', default='markov_chain.png')
    args = parser.parse_args()
    plot_markov(args.db, args.out)
