from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base

class Federation(Base):
    __tablename__ = "federations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    department = relationship("Department", back_populates="federations")
    admin = relationship("User", foreign_keys=[admin_id])
    members = relationship("User", back_populates="federation", foreign_keys="User.federation_id")
    tournaments = relationship("Tournament", back_populates="federation")
