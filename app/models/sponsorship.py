from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from ..database import Base

class Sponsorship(Base):
    __tablename__ = "sponsorships"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    sponsor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)

    # Relationships
    tournament = relationship("Tournament", back_populates="sponsorships")
    sponsor = relationship("User", back_populates="sponsorships")
