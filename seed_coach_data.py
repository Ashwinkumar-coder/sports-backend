import sys
from app.database import SessionLocal
from app.models.user import User
from app.models.tournament import Tournament
from app.models.team import Team, TeamPlayer
from app.models.federation import Federation

def seed_coach():
    db = SessionLocal()
    try:
        coach = db.query(User).filter(User.role == "coach").first()
        if not coach:
            print("No coach found. Please seed the database first.")
            return

        fed = db.query(Federation).first()
        if not fed:
            print("No federation found. Please seed the database first.")
            return

        # Create approved tournament if not exists
        tourney = db.query(Tournament).filter(Tournament.name == "IPL Premier League").first()
        if not tourney:
            tourney = Tournament(
                name="IPL Premier League",
                federation_id=fed.id,
                fee=150.0,
                number_of_entry=8,
                maximum_player_count=11,
                team_limits=15,
                is_approved=True,
                status="active"
            )
            db.add(tourney)
            db.commit()
            db.refresh(tourney)
            print("Tournament created.")
        else:
            print("Tournament already exists.")

        # Create coach's team
        team = db.query(Team).filter(Team.name == "Royal Challengers").first()
        if not team:
            team = Team(
                name="Royal Challengers",
                tournament_id=tourney.id,
                coach_id=coach.id,
                created_by_id=coach.id
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            print("Team created.")
        else:
            print("Team already exists.")
            team.coach_id = coach.id
            db.commit()

        # Get some players
        players = db.query(User).filter(User.role == "player").all()
        if not players:
            print("No players found to add.")
            return

        # Add players to team with some stats
        for i, p in enumerate(players):
            tp = db.query(TeamPlayer).filter(TeamPlayer.team_id == team.id, TeamPlayer.player_id == p.id).first()
            if not tp:
                tp = TeamPlayer(
                    team_id=team.id,
                    player_id=p.id,
                    runs_scored=100 + i * 150,
                    balls_faced=80 + i * 110,
                    wickets_taken=i,
                    runs_conceded=10 * i,
                    performance_score=(100 + i * 150) / max(1, 80 + i * 110) * 100
                )
                db.add(tp)
                print(f"Added player {p.full_name} with stats.")
        db.commit()
        print("Successfully seeded coach metrics!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_coach()
