from .database import Base 
from sqlalchemy import Column, Integer, String, Boolean


class PlayerHistory(Base):
    """Player history model"""
    __tablename__ = "player_history"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer)
    participant_id = Column(Integer)
    group = Column(Integer)
    #last_gen = Column(Boolean),
    dynasty = Column(Integer)
    DynastyGroup = Column(Integer)
    side = Column(Boolean)
    choice = Column(Boolean)
    gen = Column(Integer)
    g_advice = Column(String)
    g_survey = Column(String)
    #final = Column(Boolean)
    session_end = Column(Boolean)
    ancestor_session_id = Column(Integer, default=0)
    ancestor_participant_id = Column(Integer, default=0)
    ancestor_advice = Column(String, default="")
