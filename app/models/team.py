from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    coach_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected

    # Relationships
    tournament = relationship("Tournament", back_populates="teams")
    coach = relationship("User", foreign_keys=[coach_id], back_populates="coached_teams")
    creator = relationship("User", foreign_keys=[created_by_id], back_populates="created_teams")
    
    # Cascade deletes to team players if a team is removed
    players = relationship("TeamPlayer", back_populates="team", cascade="all, delete-orphan")

class TeamPlayer(Base):
    __tablename__ = "team_players"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Player's match performance metrics for this team/tournament
    runs_scored = Column(Integer, default=0)
    balls_faced = Column(Integer, default=0)
    wickets_taken = Column(Integer, default=0)
    runs_conceded = Column(Integer, default=0)
    performance_score = Column(Float, default=0.0)

    # Relationships
    team = relationship("Team", back_populates="players")
    player = relationship("User", foreign_keys=[player_id])
