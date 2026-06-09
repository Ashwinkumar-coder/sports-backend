from app.database import SessionLocal
from app.models.match import Match, MatchPerformance

db = SessionLocal()
match = db.query(Match).order_by(Match.id.desc()).first()
print(f"Match ID: {match.id}, Runs A: {match.team_a_runs}, Overs A: {match.team_a_overs}")
print(f"Performances:")
for p in match.performances:
    print(f"Player {p.player_id}: {p.runs_scored} runs, {p.balls_faced} balls")
