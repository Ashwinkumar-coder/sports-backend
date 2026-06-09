from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    team_a_id = Column(Integer)
    team_b_id = Column(Integer)

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    try:
        team_ids = []
        res = session.query(Match).filter(
            (Match.team_a_id.in_(team_ids)) | (Match.team_b_id.in_(team_ids))
        ).all()
        print("Success, res:", res)
    except Exception as e:
        print("Error:", e)
