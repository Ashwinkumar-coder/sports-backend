from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    federation_id = Column(Integer, ForeignKey("federations.id", ondelete="CASCADE"), nullable=False)
    
    fee = Column(Float, default=0.0)
    number_of_entry = Column(Integer, default=8)  # Maximum number of teams
    maximum_player_count = Column(Integer, default=11)  # Players per team
    team_limits = Column(Integer, default=15)  # Max squad size (e.g. including bench)
    
    is_approved = Column(Boolean, default=False)
    status = Column(String, default="pending_approval")  # pending_approval, registration_open, active, completed

    # Relationships
    federation = relationship("Federation", back_populates="tournaments")
    teams = relationship("Team", back_populates="tournament")
    matches = relationship("Match", back_populates="tournament")
    sponsorships = relationship("Sponsorship", back_populates="tournament")
