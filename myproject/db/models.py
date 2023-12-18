from .database import Base 
from sqlalchemy import Column, Integer, String


class PlayerHistory(Base):
    """Player history model"""
    __tablename__ = "player_history"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer)
    participant_id = Column(Integer)
    role_type = Column(Integer)
    choice = Column(Integer)
    advice = Column(String)
    g_survey = Column(Integer)
    ancestor_session_id = Column(Integer, default=0)
    ancestor_participant_id = Column(Integer, default=0)
    ancestor_advice = Column(String, default="")