# Markov Campus Pipeline

## Files
- `models.py`: SQLAlchemy models (Entity, Event, FaceEmbedding, Note, Transition)
- `ingest.py`: ingestion utility for profiles, events, notes, embeddings
- `train_markov.py`: builds first-order Markov transitions
- `predict.py`: query top-K next-locations for a from_loc
- `timeline.py`: show timeline for an entity_id
- `alerts.py`: list entities not seen in last N hours
- `evaluate.py`: compute Hit@K and MRR with time split
- `plot_markov.py`: draw graph of transitions
- `requirements.txt`: pip dependencies


python ingest.py --csv "student or staff profiles.csv" --source profiles --table entities
python ingest.py --csv "sorted_campus_card_swipes.csv" --source swipe --table events --entity_col card_id --location_col location_id --timestamp_col timestamp
python ingest.py --csv "wifi_associations_logs.csv" --source wifi --table events --entity_col device_hash --location_col ap_id --timestamp_col timestamp
python ingest.py --csv "cctv_frames_eda.csv" --source cctv --table events --entity_col face_id --location_col location_id --timestamp_col timestamp
python ingest.py --csv "lab_bookings_with_duration.csv" --source lab --table events --entity_col entity_id --location_col room_id --timestamp_col start_time
python ingest.py --csv "processed_library_checkouts.csv" --source library --table events --entity_col entity_id --location_col book_id --timestamp_col timestamp
python ingest.py --csv "notes_eda_full.csv" --source note --table notes
python ingest.py --csv "face_embeddings.csv" --source face --table embeddings

python train_markov.py --db sqlite:///campus_er.db

python plot_markov.py --db sqlite:///campus_er.db --out markov_chain.png

::timeline for a entity
python timeline.py --entity_id E100001 --db sqlite:///campus_er.db --out E100001_timeline.txt
::predict next location
python predict.py --db sqlite:///campus_er.db --entity_id E100001

::all entities inactive for more than 12 hrs
python alerts.py --db sqlite:///campus_er.db --hours 12

::for specififc entity
python alerts.py --db sqlite:///campus_er.db --entity_id E106975
