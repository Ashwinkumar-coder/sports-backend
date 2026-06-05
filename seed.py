import sys
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.department import Department
from app.models.federation import Federation
from app.models.tournament import Tournament
from app.models.team import Team, TeamPlayer
from app.models.match import Match
from app.core import security

def seed():
    print("Creating all tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Checking for Super Admin...")
        super_admin = db.query(User).filter(User.role == "super_admin").first()
        if not super_admin:
            super_admin = User(
                email="superadmin@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Platform Super Admin",
                role="super_admin",
                is_approved=True
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print("Super Admin created: superadmin@sports.com (password123)")
        else:
            print("Super Admin already exists.")
            
        print("Checking for Department...")
        dept = db.query(Department).first()
        if not dept:
            dept = Department(
                name="National Cricket Council",
                created_by_id=super_admin.id
            )
            db.add(dept)
            db.commit()
            db.refresh(dept)
            print("National Cricket Council Department created.")
        else:
            print("Department already exists.")
            
        print("Checking for Department Admin...")
        dept_admin = db.query(User).filter(User.role == "department_admin").first()
        if not dept_admin:
            dept_admin = User(
                email="deptadmin@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="NCC Department Admin",
                role="department_admin",
                is_approved=True,
                department_id=dept.id
            )
            db.add(dept_admin)
            db.commit()
            db.refresh(dept_admin)
            print("Department Admin created: deptadmin@sports.com (password123)")
        else:
            print("Department Admin already exists.")
            
        print("Checking for Federation Admin...")
        fed_admin = db.query(User).filter(User.role == "federation_admin").first()
        if not fed_admin:
            fed_admin = User(
                email="fedadmin@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="State Cricket Association Admin",
                role="federation_admin",
                is_approved=True,
                department_id=dept.id
            )
            db.add(fed_admin)
            db.commit()
            db.refresh(fed_admin)
            print("Federation Admin created: fedadmin@sports.com (password123)")
        else:
            print("Federation Admin already exists.")
            
        print("Checking for Federation...")
        fed = db.query(Federation).first()
        if not fed:
            fed = Federation(
                name="State Cricket Association",
                department_id=dept.id,
                admin_id=fed_admin.id
            )
            db.add(fed)
            db.commit()
            db.refresh(fed)
            
            # Link Federation Admin to Federation
            fed_admin.federation_id = fed.id
            db.commit()
            print("State Cricket Association Federation created.")
        else:
            print("Federation already exists.")

        # Seed other roles
        players_db = []
        players_data = [
            ("player1@sports.com", "Virat Kohli"),
            ("player2@sports.com", "Rohit Sharma"),
            ("player3@sports.com", "Jasprit Bumrah"),
            ("player4@sports.com", "KL Rahul"),
        ]
        for email, name in players_data:
            p = db.query(User).filter(User.email == email).first()
            if not p:
                p = User(
                    email=email,
                    hashed_password=security.get_password_hash("password123"),
                    full_name=name,
                    role="player",
                    is_approved=True
                )
                db.add(p)
                db.commit()
                db.refresh(p)
                print(f"Player created: {email}")
            players_db.append(p)

        # Coach
        coach = db.query(User).filter(User.role == "coach").first()
        if not coach:
            coach = User(
                email="coach@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Rahul Dravid",
                role="coach",
                is_approved=True
            )
            db.add(coach)
            db.commit()
            db.refresh(coach)
            print("Coach created: coach@sports.com")

        # Sponsor
        sponsor = db.query(User).filter(User.role == "sponsor").first()
        if not sponsor:
            sponsor = User(
                email="sponsor@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Adidas Sponsor",
                role="sponsor",
                is_approved=True
            )
            db.add(sponsor)
            print("Sponsor created: sponsor@sports.com")

        # Scorer
        scorer = db.query(User).filter(User.role == "scorer").first()
        if not scorer:
            scorer = User(
                email="scorer@sports.com",
                hashed_password=security.get_password_hash("password123"),
                full_name="Official Scorer Umpire",
                role="scorer",
                is_approved=True
            )
            db.add(scorer)
            db.commit()
            db.refresh(scorer)
            print("Scorer created: scorer@sports.com")

        # Seed Tournament
        tourney = db.query(Tournament).filter(Tournament.name == "SCA Premier Cup").first()
        if not tourney:
            tourney = Tournament(
                name="SCA Premier Cup",
                federation_id=fed.id,
                fee=100.0,
                number_of_entry=8,
                maximum_player_count=11,
                team_limits=15,
                is_approved=True,
                status="active"
            )
            db.add(tourney)
            db.commit()
            db.refresh(tourney)
            print("SCA Premier Cup Tournament created.")

        # Seed Teams
        team_a = db.query(Team).filter(Team.name == "Royal Challengers").first()
        if not team_a:
            team_a = Team(
                name="Royal Challengers",
                tournament_id=tourney.id,
                coach_id=coach.id,
                created_by_id=players_db[0].id
            )
            db.add(team_a)
            db.commit()
            db.refresh(team_a)
            print("Team A: Royal Challengers created.")

        team_b = db.query(Team).filter(Team.name == "Chennai Super Kings").first()
        if not team_b:
            team_b = Team(
                name="Chennai Super Kings",
                tournament_id=tourney.id,
                coach_id=coach.id,
                created_by_id=players_db[2].id
            )
            db.add(team_b)
            db.commit()
            db.refresh(team_b)
            print("Team B: Chennai Super Kings created.")

        # Add players to Team Players
        # Royal Challengers players (Virat and Rohit)
        for p in players_db[:2]:
            tp = db.query(TeamPlayer).filter(TeamPlayer.team_id == team_a.id, TeamPlayer.player_id == p.id).first()
            if not tp:
                tp = TeamPlayer(
                    team_id=team_a.id,
                    player_id=p.id,
                    runs_scored=340 if p.email == "player1@sports.com" else 280,
                    balls_faced=220 if p.email == "player1@sports.com" else 210,
                    wickets_taken=0,
                    runs_conceded=0,
                    performance_score=150.0 if p.email == "player1@sports.com" else 133.0
                )
                db.add(tp)

        # Chennai Super Kings players (Jasprit and KL)
        for p in players_db[2:]:
            tp = db.query(TeamPlayer).filter(TeamPlayer.team_id == team_b.id, TeamPlayer.player_id == p.id).first()
            if not tp:
                tp = TeamPlayer(
                    team_id=team_b.id,
                    player_id=p.id,
                    runs_scored=50 if p.email == "player3@sports.com" else 310,
                    balls_faced=40 if p.email == "player3@sports.com" else 240,
                    wickets_taken=18 if p.email == "player3@sports.com" else 0,
                    runs_conceded=180 if p.email == "player3@sports.com" else 0,
                    performance_score=145.0 if p.email == "player3@sports.com" else 129.0
                )
                db.add(tp)

        # Seed Matches
        # 1. Live Match
        match_live = db.query(Match).filter(Match.tournament_id == tourney.id, Match.status == "live").first()
        if not match_live:
            match_live = Match(
                tournament_id=tourney.id,
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                scorer_id=scorer.id,
                status="live",
                team_a_runs=142,
                team_a_wickets=3,
                team_a_overs=18.2,
                team_b_runs=0,
                team_b_wickets=0,
                team_b_overs=0.0
            )
            db.add(match_live)
            print("Live Match seeded.")

        # 2. Completed Match
        match_completed = db.query(Match).filter(Match.tournament_id == tourney.id, Match.status == "completed").first()
        if not match_completed:
            match_completed = Match(
                tournament_id=tourney.id,
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                scorer_id=scorer.id,
                status="completed",
                team_a_runs=120,
                team_a_wickets=10,
                team_a_overs=20.0,
                team_b_runs=121,
                team_b_wickets=4,
                team_b_overs=18.5,
                winner_id=team_b.id
            )
            db.add(match_completed)
            print("Completed Match seeded.")

        # Seed Notification Logs (Emails)
        from app.models.notification import NotificationLog
        log_count = db.query(NotificationLog).count()
        if log_count == 0:
            logs = [
                NotificationLog(
                    recipient_email="player1@sports.com",
                    subject="Team Registration Invitation",
                    body="Hi Virat Kohli, you have been invited to join the team 'Royal Challengers' for the 'SCA Premier Cup' by Rohit Sharma."
                ),
                NotificationLog(
                    recipient_email="coach@sports.com",
                    subject="New Team Assignment",
                    body="Hi Rahul Dravid, you have been assigned as the Coach for the team 'Royal Challengers' and 'Chennai Super Kings' in the 'SCA Premier Cup'."
                ),
                NotificationLog(
                    recipient_email="scorer@sports.com",
                    subject="Match Scoring Duty",
                    body="Hi Official Scorer Umpire, you have been assigned to score the match 'Royal Challengers' vs 'Chennai Super Kings' in the 'SCA Premier Cup'."
                )
            ]
            db.bulk_save_objects(logs)
            print("Simulated Mailbox logs seeded.")

        db.commit()
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
