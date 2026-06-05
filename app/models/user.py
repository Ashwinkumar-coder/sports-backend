from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # super_admin, department_admin, federation_admin, player, coach, sponsor, scorer
    is_approved = Column(Boolean, default=False)

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    federation_id = Column(Integer, ForeignKey("federations.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    department = relationship("Department", back_populates="members", foreign_keys=[department_id])
    federation = relationship("Federation", back_populates="members", foreign_keys=[federation_id])
    
    # Sponsorships, coached teams, etc.
    sponsorships = relationship("Sponsorship", back_populates="sponsor")
    coached_teams = relationship("Team", back_populates="coach", foreign_keys="Team.coach_id")
    created_teams = relationship("Team", back_populates="creator", foreign_keys="Team.created_by_id")
    scored_matches = relationship("Match", back_populates="scorer")
