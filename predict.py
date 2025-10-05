import argparse
from sqlalchemy import create_engine, select
from models import Transition, Event, Entity
from sqlalchemy.orm import Session

def predict_next(engine, from_loc, top_k=5):
    with engine.connect() as conn:
        stmt = (
            select(Transition.to_loc, Transition.prob)
            .where(Transition.from_loc == from_loc)
            .order_by(Transition.prob.desc())
            .limit(top_k)
        )
        rows = conn.execute(stmt).fetchall()
    return rows

def explain_prediction(from_loc, predictions, ent_name=None, ent_id=None):
    if not predictions:
        return f"No transitions found from {from_loc}. This may mean there is not enough historical data."
    
    name_str = f" for {ent_name} ({ent_id})" if ent_name else ""
    explanation = f"Based on historical movement patterns{name_str}, after being at **{from_loc}**, the most likely next locations are:\n"
    for i, (loc, prob) in enumerate(predictions, start=1):
        explanation += f"  {i}. {loc} with {prob:.1%} probability\n"
    
    top_choice, top_prob = predictions[0]
    explanation += f"\n👉 This suggests the entity is most likely heading to **{top_choice}** (confidence {top_prob:.1%}).\n"
    explanation += "These probabilities are inferred from past sequences of swipes, WiFi logs, and CCTV events sorted in time."
    return explanation

def get_last_location(engine, entity_id):
    with Session(engine) as session:
        ev = (
            session.query(Event)
            .filter(Event.entity_id == str(entity_id))
            .order_by(Event.timestamp.desc())
            .first()
        )
        if not ev:
            return None, None
        ent = session.query(Entity).filter(Entity.entity_id == str(entity_id)).first()
        return ev.location, ent.name if ent else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="sqlite:///campus_er.db")
    parser.add_argument("--from_loc", help="Starting location")
    parser.add_argument("--entity_id", help="Entity ID to predict from last location")
    parser.add_argument("--top_k", type=int, default=5)
    args = parser.parse_args()

    engine = create_engine(args.db)

    if args.entity_id:
        from_loc, ent_name = get_last_location(engine, args.entity_id)
        if not from_loc:
            print(f"No events found for entity {args.entity_id}")
            exit()
        preds = predict_next(engine, from_loc, args.top_k)
        print(f"=== Raw Predictions for {args.entity_id} (last seen at {from_loc}) ===")
        for to_loc, prob in preds:
            print(f"{from_loc} → {to_loc}: {prob:.2f}")
        print("\n=== Natural Language Explanation ===")
        print(explain_prediction(from_loc, preds, ent_name, args.entity_id))
    elif args.from_loc:
        preds = predict_next(engine, args.from_loc, args.top_k)
        print(f"=== Raw Predictions from {args.from_loc} ===")
        for to_loc, prob in preds:
            print(f"{args.from_loc} → {to_loc}: {prob:.2f}")
        print("\n=== Natural Language Explanation ===")
        print(explain_prediction(args.from_loc, preds))
    else:
        print("You must provide either --entity_id or --from_loc")
