from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    team_a_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team_b_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    scorer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(String, default="scheduled")  # scheduled, live, completed
    
    # Live Cricket Scoreboard
    team_a_runs = Column(Integer, default=0)
    team_a_wickets = Column(Integer, default=0)
    team_a_overs = Column(Float, default=0.0)
    
    team_b_runs = Column(Integer, default=0)
    team_b_wickets = Column(Integer, default=0)
    team_b_overs = Column(Float, default=0.0)
    
    winner_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    tournament = relationship("Tournament", back_populates="matches")
    team_a = relationship("Team", foreign_keys=[team_a_id])
    team_b = relationship("Team", foreign_keys=[team_b_id])
    scorer = relationship("User", foreign_keys=[scorer_id], back_populates="scored_matches")
    winner = relationship("Team", foreign_keys=[winner_id])
