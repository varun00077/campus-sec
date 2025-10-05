from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Float, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True)
    entity_id = Column(String, unique=True, index=True)
    student_id = Column(String, index=True, nullable=True)
    staff_id = Column(String, index=True, nullable=True)
    card_id = Column(String, index=True, nullable=True)
    device_hash = Column(String, index=True, nullable=True)
    face_id = Column(String, index=True, nullable=True)
    name = Column(String)
    role = Column(String)
    email = Column(String)
    extra_metadata = Column(JSON)   # 👈 renamed from 'metadata'


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    entity_id = Column(String, index=True, nullable=True)   # resolved canonical id if available
    raw_id = Column(String, index=True, nullable=True)      # raw identifier (card/device/face)
    source = Column(String, index=True)                     # 'swipe','wifi','cctv','lab','library','note'
    location = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    raw = Column(JSON)

    __table_args__ = (
        Index("ix_events_entity_time", "entity_id", "timestamp"),
    )

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id = Column(Integer, primary_key=True)
    face_id = Column(String, index=True, nullable=True)
    entity_id = Column(String, index=True, nullable=True)
    camera_id = Column(String, index=True, nullable=True)
    timestamp = Column(DateTime, index=True, nullable=True)
    vector = Column(JSON)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    note_id = Column(String, index=True, nullable=True)
    entity_id = Column(String, index=True, nullable=True)
    timestamp = Column(DateTime, index=True, nullable=True)
    category = Column(String)
    text = Column(String)

class Transition(Base):
    __tablename__ = "transitions"
    id = Column(Integer, primary_key=True)
    from_loc = Column(String, index=True)
    to_loc = Column(String, index=True)
    count = Column(Integer, default=0)
    prob = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

def get_engine(db_url="sqlite:///campus_er.db"):
    return create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {}
    )

def init_db(db_url="sqlite:///campus_er.db"):
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine

def get_session(db_url="sqlite:///campus_er.db"):
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()
