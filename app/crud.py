from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from .models.user import User
from .models.department import Department
from .models.federation import Federation
from .models.tournament import Tournament
from .models.team import Team, TeamPlayer
from .models.match import Match
from .models.sponsorship import Sponsorship
from .models.notification import NotificationLog
from . import schemas
from .core.security import get_password_hash

# Authentication & Users
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_in: schemas.UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    # If role is super_admin or department_admin, they are approved automatically.
    # Otherwise, they need approval from a Department Admin.
    is_approved = user_in.role in ["super_admin", "department_admin"]
    
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        is_approved=is_approved,
        department_id=user_in.department_id,
        federation_id=user_in.federation_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_pending_registrations(db: Session) -> List[User]:
    return db.query(User).filter(User.is_approved == False).all()

def approve_user(db: Session, user_id: int) -> Optional[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.is_approved = True
        db.commit()
        db.refresh(db_user)
        # Log approval notification email
        log_notification(
            db,
            recipient_email=db_user.email,
            subject="Account Approved",
            body=f"Hello {db_user.full_name},\n\nYour account registration for the role of '{db_user.role}' has been approved by the Department Admin. You can now log in."
        )
    return db_user

def get_users_by_role(db: Session, role: str) -> List[User]:
    return db.query(User).filter(User.role == role, User.is_approved == True).all()


# Departments
def create_department(db: Session, dept_in: schemas.DepartmentCreate, creator_id: int) -> Department:
    db_dept = Department(name=dept_in.name, created_by_id=creator_id)
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept

def get_departments(db: Session) -> List[Department]:
    return db.query(Department).all()


# Federations
def create_federation(db: Session, fed_in: schemas.FederationCreate, department_id: int) -> Federation:
    db_fed = Federation(
        name=fed_in.name,
        department_id=department_id,
        admin_id=fed_in.admin_id
    )
    db.add(db_fed)
    db.commit()
    db.refresh(db_fed)
    return db_fed

def get_federations(db: Session) -> List[Federation]:
    return db.query(Federation).all()


# Tournaments
def create_tournament(db: Session, tourney_in: schemas.TournamentCreate, federation_id: int) -> Tournament:
    db_tourney = Tournament(
        name=tourney_in.name,
        federation_id=federation_id,
        fee=tourney_in.fee,
        number_of_entry=tourney_in.number_of_entry,
        maximum_player_count=tourney_in.maximum_player_count,
        team_limits=tourney_in.team_limits,
        is_approved=False,
        status="pending_approval"
    )
    db.add(db_tourney)
    db.commit()
    db.refresh(db_tourney)
    
    # Notify Department Admin about the new tournament
    # Get all department admins to email
    dept_admins = db.query(User).filter(User.role == "department_admin").all()
    for admin in dept_admins:
        log_notification(
            db,
            recipient_email=admin.email,
            subject="New Tournament Created - Action Required",
            body=f"Federation Admin created a new tournament: '{db_tourney.name}'. Please log in to approve it so registration can open."
        )
    return db_tourney

def get_tournaments(db: Session, approved_only: bool = True) -> List[Tournament]:
    if approved_only:
        return db.query(Tournament).filter(Tournament.is_approved == True).all()
    return db.query(Tournament).all()

def get_pending_tournaments(db: Session) -> List[Tournament]:
    return db.query(Tournament).filter(Tournament.is_approved == False).all()

def approve_tournament(db: Session, tournament_id: int) -> Optional[Tournament]:
    db_tourney = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if db_tourney:
        db_tourney.is_approved = True
        db_tourney.status = "registration_open"
        db.commit()
        db.refresh(db_tourney)
        
        # Log notification email
        # Retrieve federation admin email
        fed_admin = db_tourney.federation.admin
        if fed_admin:
            log_notification(
                db,
                recipient_email=fed_admin.email,
                subject="Tournament Approved",
                body=f"Your tournament '{db_tourney.name}' has been approved by the Department Admin. Registration is now open."
            )
    return db_tourney


# Team Registrations
def create_team(db: Session, team_in: schemas.TeamCreate, tournament_id: int, creator_id: int) -> Team:
    db_team = Team(
        name=team_in.name,
        tournament_id=tournament_id,
        coach_id=team_in.coach_id,
        created_by_id=creator_id
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    # Add team players
    for player_id in team_in.player_ids:
        team_player = TeamPlayer(
            team_id=db_team.id,
            player_id=player_id,
            runs_scored=0,
            balls_faced=0,
            wickets_taken=0,
            runs_conceded=0,
            performance_score=0.0
        )
        db.add(team_player)
    db.commit()
    db.refresh(db_team)

    # Trigger notifications:
    # 1. To the Coach
    coach = db.query(User).filter(User.id == team_in.coach_id).first()
    if coach:
        log_notification(
            db,
            recipient_email=coach.email,
            subject="Selected as Coach for Tournament Team",
            body=f"Hello Coach {coach.full_name},\n\nYou have been selected by {db_team.creator.full_name} to coach their team '{db_team.name}' in the tournament '{db_team.tournament.name}'."
        )

    # 2. To team players
    for player_id in team_in.player_ids:
        player = db.query(User).filter(User.id == player_id).first()
        if player:
            log_notification(
                db,
                recipient_email=player.email,
                subject="You have been added to a Tournament Team",
                body=f"Hello {player.full_name},\n\nYou have been registered for the team '{db_team.name}' in the tournament '{db_team.tournament.name}' under Coach {coach.full_name if coach else 'N/A'}."
            )
            
    # 3. Notification of registration completion to Sponsor & Scorer assigned (simulated/generic)
    # Find active sponsors for the tournament
    sponsorships = db.query(Sponsorship).filter(Sponsorship.tournament_id == tournament_id).all()
    for s in sponsorships:
        log_notification(
            db,
            recipient_email=s.sponsor.email,
            subject="New Team Registered in Sponsored Tournament",
            body=f"A new team '{db_team.name}' has registered for '{db_team.tournament.name}', which you sponsor."
        )

    return db_team

def get_teams_for_tournament(db: Session, tournament_id: int) -> List[Team]:
    return db.query(Team).filter(Team.tournament_id == tournament_id).all()


# Matches
def create_match(db: Session, match_in: schemas.MatchCreate, tournament_id: int) -> Match:
    db_match = Match(
        tournament_id=tournament_id,
        team_a_id=match_in.team_a_id,
        team_b_id=match_in.team_b_id,
        scorer_id=match_in.scorer_id,
        status="scheduled"
    )
    db.add(db_match)
    db.commit()
    db.refresh(db_match)

    # Notify Scorer
    scorer = db.query(User).filter(User.id == match_in.scorer_id).first()
    if scorer:
        log_notification(
            db,
            recipient_email=scorer.email,
            subject="Assigned as Scorer/Umpire",
            body=f"You have been assigned as the Scorer for the match between {db_match.team_a.name} and {db_match.team_b.name} in the tournament '{db_match.tournament.name}'."
        )
    return db_match

def get_matches(db: Session) -> List[Match]:
    return db.query(Match).all()

def update_match_score(db: Session, match_id: int, score_in: schemas.ScoreUpdate) -> Optional[Match]:
    db_match = db.query(Match).filter(Match.id == match_id).first()
    if not db_match:
        return None
    
    db_match.status = "live"
    if score_in.team == "team_a":
        db_match.team_a_runs = score_in.runs
        db_match.team_a_wickets = score_in.wickets
        db_match.team_a_overs = score_in.overs
    elif score_in.team == "team_b":
        db_match.team_b_runs = score_in.runs
        db_match.team_b_wickets = score_in.wickets
        db_match.team_b_overs = score_in.overs
        
    db.commit()
    db.refresh(db_match)
    return db_match

def complete_match(db: Session, match_id: int, complete_in: schemas.MatchCompleteInput) -> Optional[Match]:
    db_match = db.query(Match).filter(Match.id == match_id).first()
    if not db_match:
        return None
        
    db_match.status = "completed"
    db_match.winner_id = complete_in.winner_id
    
    # Process and record player performances
    for p_perf in complete_in.performances:
        # Calculate performance score based on formula:
        # Score = (Runs * 1.0) + (Wickets * 20) + (Balls Faced * 0.1) - (Runs Conceded * 0.5)
        perf_score = (
            (p_perf.runs_scored * 1.0) + 
            (p_perf.wickets_taken * 20.0) + 
            (p_perf.balls_faced * 0.1) - 
            (p_perf.runs_conceded * 0.5)
        )
        
        # Save to TeamPlayer table. First locate the TeamPlayer object for player in either team A or team B
        tp = db.query(TeamPlayer).filter(
            TeamPlayer.player_id == p_perf.player_id,
            TeamPlayer.team_id.in_([db_match.team_a_id, db_match.team_b_id])
        ).first()
        
        if tp:
            # Accumulate performance since players can play multiple games in a tournament
            tp.runs_scored += p_perf.runs_scored
            tp.balls_faced += p_perf.balls_faced
            tp.wickets_taken += p_perf.wickets_taken
            tp.runs_conceded += p_perf.runs_conceded
            tp.performance_score += perf_score
            db.add(tp)
            
    db.commit()
    db.refresh(db_match)
    
    # Notify team creators and coach about completion
    coach_a = db_match.team_a.coach
    coach_b = db_match.team_b.coach
    
    if coach_a:
        log_notification(
            db,
            recipient_email=coach_a.email,
            subject="Match Completed - Performance Analysis Ready",
            body=f"The match between your team '{db_match.team_a.name}' and '{db_match.team_b.name}' is complete. Check your dashboard to view player stats."
        )
    if coach_b:
        log_notification(
            db,
            recipient_email=coach_b.email,
            subject="Match Completed - Performance Analysis Ready",
            body=f"The match between your team '{db_match.team_b.name}' and '{db_match.team_a.name}' is complete. Check your dashboard to view player stats."
        )

    # Mark the tournament as completed if all matches are completed (simplified POC check)
    # Check if there are matches in this tournament, if all of them are completed, mark tournament completed
    tournament_matches = db.query(Match).filter(Match.tournament_id == db_match.tournament_id).all()
    if all(m.status == "completed" for m in tournament_matches):
        tourney = db_match.tournament
        tourney.status = "completed"
        db.commit()
        
    return db_match


# Sponsorships
def create_sponsorship(db: Session, amount: float, tournament_id: int, sponsor_id: int) -> Sponsorship:
    db_sponsorship = Sponsorship(
        tournament_id=tournament_id,
        sponsor_id=sponsor_id,
        amount=amount
    )
    db.add(db_sponsorship)
    db.commit()
    db.refresh(db_sponsorship)
    return db_sponsorship


# Notification Logs
def log_notification(db: Session, recipient_email: str, subject: str, body: str) -> NotificationLog:
    log = NotificationLog(
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        sent_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_notifications(db: Session) -> List[NotificationLog]:
    return db.query(NotificationLog).order_by(NotificationLog.sent_at.desc()).all()
