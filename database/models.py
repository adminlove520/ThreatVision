from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

Base = declarative_base()

class CVERecord(Base):
    __tablename__ = 'cve_records'

    id = Column(Integer, primary_key=True)
    cve_id = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    cvss_score = Column(Float)
    publish_time = Column(DateTime)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    repo_url = Column(String(255))
    ai_analysis = Column(Text) # JSON string
    is_high_value = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<CVERecord(cve_id='{self.cve_id}')>"

class Repository(Base):
    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    stars = Column(Integer, default=0)
    last_updated = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_high_value = Column(Boolean, default=False)
    ai_analysis = Column(Text) # JSON string

    def __repr__(self):
        return f"<Repository(name='{self.name}')>"

def init_db():
    """Initialize databases"""
    # CVE Database
    engine_cve = create_engine(f'sqlite:///{Config.DB_PATH_CVE}')
    CVERecord.metadata.create_all(engine_cve)
    
    # Repo Database
    engine_repo = create_engine(f'sqlite:///{Config.DB_PATH_REPO}')
    Repository.metadata.create_all(engine_repo)
    
    return engine_cve, engine_repo

_session_makers = {}

def get_session(engine):
    if engine not in _session_makers:
        _session_makers[engine] = sessionmaker(bind=engine)
    return _session_makers[engine]()
