import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from sqlalchemy import create_engine

# Step 1: Load sequences from DB
engine = create_engine("sqlite:///campus_er.db")
df = pd.read_sql("SELECT entity_id, location, timestamp FROM events ORDER BY entity_id, timestamp", engine)

# Encode locations as integers
loc2idx = {loc: i for i, loc in enumerate(df['location'].dropna().unique())}
idx2loc = {i: loc for loc, i in loc2idx.items()}
df['loc_idx'] = df['location'].map(loc2idx)

# Group sequences per entity
sequences = df.groupby('entity_id')['loc_idx'].apply(list).tolist()

# Build training data (X=sequence[:-1], y=sequence[1:])
X, y = [], []
for seq in sequences:
    if len(seq) > 2:
        X.append(seq[:-1])
        y.append(seq[1:])

# Pad sequences
from torch.nn.utils.rnn import pad_sequence
X_tensors = [torch.tensor(x, dtype=torch.long) for x in X]
y_tensors = [torch.tensor(x, dtype=torch.long) for x in y]
X_padded = pad_sequence(X_tensors, batch_first=True)
y_padded = pad_sequence(y_tensors, batch_first=True)

# Step 2: Define RNN model
class LocationRNN(nn.Module):
    def __init__(self, vocab_size, embed_size=32, hidden_size=64):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_size)
        self.rnn = nn.GRU(embed_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, vocab_size)

    def forward(self, x):
        x = self.embedding(x)
        out, _ = self.rnn(x)
        out = self.fc(out)
        return out

vocab_size = len(loc2idx)
model = LocationRNN(vocab_size)
criterion = nn.CrossEntropyLoss(ignore_index=0)
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Step 3: Train
for epoch in range(5):  # increase epochs later
    optimizer.zero_grad()
    outputs = model(X_padded)
    loss = criterion(outputs.view(-1, vocab_size), y_padded.view(-1))
    loss.backward()
    optimizer.step()
    print(f"Epoch {epoch+1}, Loss: {loss.item():.4f}")

# Step 4: Predict next location
def predict_next(seq, top_k=3):
    with torch.no_grad():
        seq_idx = torch.tensor([loc2idx[s] for s in seq], dtype=torch.long).unsqueeze(0)
        outputs = model(seq_idx)
        last_output = outputs[0, -1]
        probs = torch.softmax(last_output, dim=0)
        top_idx = probs.topk(top_k).indices.tolist()
        return [(idx2loc[i], probs[i].item()) for i in top_idx]

print(predict_next(["LIB_ENT", "CAF_01"]))
