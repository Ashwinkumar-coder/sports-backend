from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from . import crud, schemas
from .core import deps, security
from .models.user import User
from .models.department import Department
from .models.federation import Federation
from .models.tournament import Tournament
from .models.team import Team, TeamPlayer
from .models.match import Match
from .models.sponsorship import Sponsorship
from .models.notification import NotificationLog

api_router = APIRouter()

# ----------------------------------------------------
# 1. Authentication & Users
# ----------------------------------------------------

@api_router.post("/auth/register", response_model=schemas.UserOut)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    db_user = crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    return crud.create_user(db, user_in=user_in)

@api_router.post("/auth/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    
    # Check if the user is approved (except super admin and department admin)
    if user.role != "super_admin" and user.role != "department_admin" and not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is pending approval by the Department admin."
        )

    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@api_router.get("/auth/me", response_model=schemas.UserOut)
def read_user_me(current_user: User = Depends(deps.get_current_user)):
    return current_user

@api_router.get("/auth/users", response_model=List[schemas.UserOut])
def get_users_list(
    role: Optional[str] = None,
    all_users: Optional[bool] = False,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Retrieve approved users (or all users if requested by admin)."""
    if all_users and current_user.role in ["super_admin", "department_admin"]:
        query = db.query(User)
    else:
        query = db.query(User).filter(User.is_approved == True)
    if role:
        query = query.filter(User.role == role)
    return query.all()


# ----------------------------------------------------
# 2. Super Admin
# ----------------------------------------------------

@api_router.post("/superadmin/departments", response_model=schemas.DepartmentOut)
def create_department_endpoint(
    dept_in: schemas.DepartmentCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Admins can create departments.")
    return crud.create_department(db, dept_in=dept_in, creator_id=current_user.id)

@api_router.get("/departments", response_model=List[schemas.DepartmentOut])
def list_departments(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return crud.get_departments(db)


# ----------------------------------------------------
# 3. Department Admin (Approvals & Federations)
# ----------------------------------------------------

@api_router.post("/departments/{dept_id}/federations", response_model=schemas.FederationOut)
def create_federation_endpoint(
    dept_id: int,
    fed_in: schemas.FederationCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "department_admin":
        raise HTTPException(status_code=403, detail="Only Department Admins can create federations.")
    return crud.create_federation(db, fed_in=fed_in, department_id=dept_id)

@api_router.get("/federations", response_model=List[schemas.FederationOut])
def list_federations(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return crud.get_federations(db)

@api_router.get("/department/pending-registrations", response_model=List[schemas.UserOut])
def get_pending_regs(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "department_admin":
        raise HTTPException(status_code=403, detail="Only Department Admins can view approvals.")
    return crud.get_pending_registrations(db)

@api_router.post("/department/approve-registration/{user_id}", response_model=schemas.UserOut)
def approve_user_reg(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "department_admin":
        raise HTTPException(status_code=403, detail="Only Department Admins can approve registrations.")
    approved = crud.approve_user(db, user_id=user_id)
    if not approved:
        raise HTTPException(status_code=404, detail="User not found.")
    return approved

@api_router.get("/department/pending-tournaments", response_model=List[schemas.TournamentOut])
def get_pending_tourneys(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "department_admin":
        raise HTTPException(status_code=403, detail="Only Department Admins can view pending tournaments.")
    return crud.get_pending_tournaments(db)

@api_router.post("/department/approve-tournament/{tournament_id}", response_model=schemas.TournamentOut)
def approve_tournament_reg(
    tournament_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "department_admin":
        raise HTTPException(status_code=403, detail="Only Department Admins can approve tournaments.")
    approved = crud.approve_tournament(db, tournament_id=tournament_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Tournament not found.")
    return approved


# ----------------------------------------------------
# 4. Tournaments & Sponsorships
# ----------------------------------------------------

@api_router.post("/tournaments", response_model=schemas.TournamentOut)
def create_tournament_endpoint(
    tourney_in: schemas.TournamentCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "federation_admin":
        raise HTTPException(status_code=403, detail="Only Federation Admins can create tournaments.")
    if not current_user.federation_id:
        raise HTTPException(status_code=400, detail="Federation Admin is not assigned to any Federation.")
    return crud.create_tournament(db, tourney_in=tourney_in, federation_id=current_user.federation_id)

@api_router.get("/tournaments", response_model=List[schemas.TournamentOut])
def list_approved_tournaments(db: Session = Depends(deps.get_db)):
    return crud.get_tournaments(db, approved_only=True)

@api_router.get("/tournaments/all", response_model=List[schemas.TournamentOut])
def list_all_tournaments(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return crud.get_tournaments(db, approved_only=False)

@api_router.post("/tournaments/{id}/register-team", response_model=schemas.TeamOut)
def register_team_endpoint(
    id: int,
    team_in: schemas.TeamCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "player":
        raise HTTPException(status_code=403, detail="Only Players can register teams.")
    
    tourney = db.query(Tournament).filter(Tournament.id == id).first()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found.")
    if not tourney.is_approved:
        raise HTTPException(status_code=400, detail="Tournament is not approved yet.")
        
    # Check registration limit
    current_teams = len(tourney.teams)
    if current_teams >= tourney.number_of_entry:
        raise HTTPException(status_code=400, detail="Tournament registration is full.")
        
    # Check if coach is already booked
    coach_booked = db.query(Team).filter(
        Team.tournament_id == id,
        Team.coach_id == team_in.coach_id
    ).first()
    if coach_booked:
        raise HTTPException(status_code=400, detail="Coach is already booked for this tournament.")

    # Check if any player is already booked
    for pid in team_in.player_ids:
        player_booked = db.query(TeamPlayer).join(Team).filter(
            Team.tournament_id == id,
            TeamPlayer.player_id == pid
        ).first()
        if player_booked:
            player_user = db.query(User).filter(User.id == pid).first()
            pname = player_user.full_name if player_user else f"ID {pid}"
            raise HTTPException(status_code=400, detail=f"Player '{pname}' is already booked.")
            
    return crud.create_team(db, team_in=team_in, tournament_id=id, creator_id=current_user.id)

@api_router.get("/tournaments/{id}/teams", response_model=List[schemas.TeamOut])
def list_tournament_teams(id: int, db: Session = Depends(deps.get_db)):
    return crud.get_teams_for_tournament(db, tournament_id=id)

@api_router.post("/tournaments/{id}/sponsor", response_model=schemas.SponsorshipOut)
def sponsor_tournament_endpoint(
    id: int,
    sponsor_in: schemas.SponsorshipCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "sponsor":
        raise HTTPException(status_code=403, detail="Only Sponsors can fund tournaments.")
    tourney = db.query(Tournament).filter(Tournament.id == id).first()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found.")
    return crud.create_sponsorship(db, amount=sponsor_in.amount, tournament_id=id, sponsor_id=current_user.id)


# ----------------------------------------------------
# 5. Matches & Scoring (Scorer)
# ----------------------------------------------------

@api_router.post("/tournaments/{id}/matches", response_model=schemas.MatchOut)
def create_match_endpoint(
    id: int,
    match_in: schemas.MatchCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "federation_admin":
        raise HTTPException(status_code=403, detail="Only Federation Admins can schedule matches.")
    
    tourney = db.query(Tournament).filter(Tournament.id == id).first()
    if not tourney:
        raise HTTPException(status_code=404, detail="Tournament not found.")
        
    # Verify teams are registered in this tournament
    team_a = db.query(Team).filter(Team.id == match_in.team_a_id, Team.tournament_id == id).first()
    team_b = db.query(Team).filter(Team.id == match_in.team_b_id, Team.tournament_id == id).first()
    if not team_a or not team_b:
        raise HTTPException(status_code=400, detail="One or both teams are not registered in this tournament.")
        
    return crud.create_match(db, match_in=match_in, tournament_id=id)

@api_router.get("/tournaments/{id}/matches", response_model=List[schemas.MatchOut])
def list_tournament_matches(id: int, db: Session = Depends(deps.get_db)):
    matches = db.query(Match).options(joinedload(Match.scorer)).filter(Match.tournament_id == id).all()
    return matches

@api_router.get("/matches", response_model=List[schemas.MatchOut])
def list_matches(db: Session = Depends(deps.get_db)):
    return crud.get_matches(db)

@api_router.get("/matches/{match_id}", response_model=schemas.MatchOut)
def get_match_by_id(match_id: int, db: Session = Depends(deps.get_db)):
    match = db.query(Match).options(joinedload(Match.scorer)).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
    return match

@api_router.post("/matches/{match_id}/score", response_model=schemas.MatchOut)
def update_score_endpoint(
    match_id: int,
    score_in: schemas.ScoreUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "scorer":
        raise HTTPException(status_code=403, detail="Only assigned Scorers can update scores.")
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
    if match.scorer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned Scorer for this match.")
        
    updated = crud.update_match_score(db, match_id=match_id, score_in=score_in)
    return updated

@api_router.post("/matches/{match_id}/complete", response_model=schemas.MatchOut)
def complete_match_endpoint(
    match_id: int,
    complete_in: schemas.MatchCompleteInput,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "scorer":
        raise HTTPException(status_code=403, detail="Only assigned Scorers can complete matches.")
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
    if match.scorer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned Scorer for this match.")
        
    completed = crud.complete_match(db, match_id=match_id, complete_in=complete_in)
    return completed


# ----------------------------------------------------
# 6. Dashboards
# ----------------------------------------------------

@api_router.get("/dashboard/player")
def get_player_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "player":
        raise HTTPException(status_code=400, detail="Invalid role for this dashboard.")
        
    # Get all teams player is in
    team_players = db.query(TeamPlayer).filter(TeamPlayer.player_id == current_user.id).all()
    team_ids = [tp.team_id for tp in team_players]
    
    # Names of teams they played for
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
    team_names = [t.name for t in teams]
    
    # Matches played, won, lost
    matches_played = 0
    matches_won = 0
    matches_lost = 0
    
    completed_matches = db.query(Match).filter(
        Match.status == "completed",
        (Match.team_a_id.in_(team_ids)) | (Match.team_b_id.in_(team_ids))
    ).all()
    
    matches_played = len(completed_matches)
    for m in completed_matches:
        # Check if the player's team won
        if m.winner_id in team_ids:
            matches_won += 1
        elif m.winner_id is not None:
            matches_lost += 1
            
    # Accumulate player metrics
    total_runs = sum(tp.runs_scored for tp in team_players)
    total_balls = sum(tp.balls_faced for tp in team_players)
    total_wickets = sum(tp.wickets_taken for tp in team_players)
    total_runs_conceded = sum(tp.runs_conceded for tp in team_players)
    overall_performance = sum(tp.performance_score for tp in team_players)
            
    return {
        "matches_played": matches_played,
        "matches_won": matches_won,
        "matches_lost": matches_lost,
        "team_names": team_names,
        "total_runs": total_runs,
        "total_balls": total_balls,
        "total_wickets": total_wickets,
        "total_runs_conceded": total_runs_conceded,
        "overall_performance": overall_performance
    }

@api_router.get("/dashboard/coach")
def get_coach_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "coach":
        raise HTTPException(status_code=400, detail="Invalid role for this dashboard.")
        
    # Teams coached
    coached_teams = db.query(Team).filter(Team.coach_id == current_user.id).all()
    coached_team_ids = [t.id for t in coached_teams]
    teams_trained_count = len(coached_teams)
    
    # Players trained (unique users)
    team_players = db.query(TeamPlayer).filter(TeamPlayer.team_id.in_(coached_team_ids)).all() if coached_team_ids else []
    
    player_stats_map = {}
    for tp in team_players:
        p_id = tp.player_id
        if p_id not in player_stats_map:
            player_stats_map[p_id] = {
                "player_id": p_id,
                "full_name": tp.player.full_name,
                "email": tp.player.email,
                "runs_scored": 0,
                "balls_faced": 0,
                "wickets_taken": 0,
                "runs_conceded": 0,
                "performance_score": 0.0,
                "teams": []
            }
        
        player_stats_map[p_id]["runs_scored"] += tp.runs_scored
        player_stats_map[p_id]["balls_faced"] += tp.balls_faced
        player_stats_map[p_id]["wickets_taken"] += tp.wickets_taken
        player_stats_map[p_id]["runs_conceded"] += tp.runs_conceded
        player_stats_map[p_id]["performance_score"] += tp.performance_score
        player_stats_map[p_id]["teams"].append(tp.team.name)
        
    # Convert map to list and sort by performance_score descending
    players_list = list(player_stats_map.values())
    players_list.sort(key=lambda x: x["performance_score"], reverse=True)
    
    return {
        "teams_trained_count": teams_trained_count,
        "players_trained_count": len(players_list),
        "players": players_list,
        "coached_teams": [
            {
                "id": t.id,
                "name": t.name,
                "tournament_name": t.tournament.name,
                "player_count": len(t.players)
            } for t in coached_teams
        ]
    }

@api_router.get("/dashboard/sponsor")
def get_sponsor_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "sponsor":
        raise HTTPException(status_code=400, detail="Invalid role for this dashboard.")
        
    sponsorships = db.query(Sponsorship).filter(Sponsorship.sponsor_id == current_user.id).all()
    
    sponsored_items = []
    total_sponsored = 0.0
    for s in sponsorships:
        sponsored_items.append({
            "id": s.id,
            "tournament_name": s.tournament.name,
            "tournament_status": s.tournament.status,
            "amount": s.amount
        })
        total_sponsored += s.amount
        
    return {
        "total_sponsored": total_sponsored,
        "sponsorships": sponsored_items
    }

@api_router.get("/dashboard/scorer")
def get_scorer_dashboard(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "scorer":
        raise HTTPException(status_code=400, detail="Invalid role for this dashboard.")
        
    assigned_matches = db.query(Match).filter(Match.scorer_id == current_user.id).all()
    
    matches_list = []
    for m in assigned_matches:
        match_data = schemas.MatchOut.model_validate(m).model_dump()
        match_data["tournament_name"] = m.tournament.name
        match_data["team_a_name"] = m.team_a.name
        match_data["team_b_name"] = m.team_b.name
        match_data["score_summary"] = f"{m.team_a.name}: {m.team_a_runs}/{m.team_a_wickets} ({m.team_a_overs} ov) vs {m.team_b.name}: {m.team_b_runs}/{m.team_b_wickets} ({m.team_b_overs} ov)"
        matches_list.append(match_data)
        
    return {
        "assigned_matches": matches_list
    }


# ----------------------------------------------------
# Scorer applications, Sponsorship approvals, Team approvals, and admin delete/block
# ----------------------------------------------------

@api_router.post("/tournaments/{tournament_id}/apply-scorer", response_model=schemas.ScorerApplicationOut)
def apply_scorer_endpoint(
    tournament_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "scorer":
        raise HTTPException(status_code=403, detail="Only scorers can apply.")
    return crud.apply_scorer(db, tournament_id=tournament_id, scorer_id=current_user.id)

@api_router.get("/federation/pending-teams", response_model=List[schemas.TeamOut])
def get_pending_teams(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["federation_admin", "super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    return db.query(Team).filter(Team.status == "pending").all()

@api_router.get("/federation/pending-sponsorships", response_model=List[schemas.SponsorshipOut])
def get_pending_sponsorships(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["federation_admin", "super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    return db.query(Sponsorship).filter(Sponsorship.status == "pending").all()

@api_router.get("/federation/pending-scorers", response_model=List[schemas.ScorerApplicationOut])
def get_pending_scorers(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["federation_admin", "super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    from .models.scorer_application import ScorerApplication
    return db.query(ScorerApplication).filter(ScorerApplication.status == "pending").all()

@api_router.post("/federation/teams/{team_id}/approve", response_model=schemas.TeamOut)
def approve_team_endpoint(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["federation_admin", "department_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    approved = crud.approve_team(db, team_id=team_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Team not found.")
    return approved

@api_router.post("/federation/sponsorships/{sponsorship_id}/approve", response_model=schemas.SponsorshipOut)
def approve_sponsorship_endpoint(
    sponsorship_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["federation_admin", "department_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    approved = crud.approve_sponsorship(db, sponsorship_id=sponsorship_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Sponsorship not found.")
    return approved

@api_router.post("/federation/scorers/{application_id}/approve", response_model=schemas.ScorerApplicationOut)
def approve_scorer_endpoint(
    application_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["federation_admin", "department_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    approved = crud.approve_scorer(db, application_id=application_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Scorer application not found.")
    return approved

# Admin deletions & blocking
@api_router.delete("/admin/users/{user_id}")
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"status": "success"}

@api_router.post("/admin/users/{user_id}/block", response_model=schemas.UserOut)
def block_user_endpoint(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    blocked = crud.block_user(db, user_id=user_id)
    if not blocked:
        raise HTTPException(status_code=404, detail="User not found.")
    return blocked

@api_router.post("/admin/users/{user_id}/unblock", response_model=schemas.UserOut)
def unblock_user_endpoint(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    unblocked = crud.unblock_user(db, user_id=user_id)
    if not unblocked:
        raise HTTPException(status_code=404, detail="User not found.")
    return unblocked


@api_router.delete("/admin/matches/{match_id}")
def delete_match_endpoint(
    match_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    success = crud.delete_match(db, match_id=match_id)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found.")
    return {"status": "success"}

@api_router.delete("/admin/federations/{fed_id}")
def delete_federation_endpoint(
    fed_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    success = crud.delete_federation(db, federation_id=fed_id)
    if not success:
        raise HTTPException(status_code=404, detail="Federation not found.")
    return {"status": "success"}

@api_router.delete("/admin/tournaments/{tourney_id}")
def delete_tournament_endpoint(
    tourney_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role not in ["super_admin", "department_admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    success = crud.delete_tournament(db, tournament_id=tourney_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tournament not found.")
    return {"status": "success"}

@api_router.get("/scorer/applications", response_model=List[schemas.ScorerApplicationOut])
def get_scorer_applications(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "scorer":
        raise HTTPException(status_code=403, detail="Access denied.")
    from .models.scorer_application import ScorerApplication
    return db.query(ScorerApplication).filter(ScorerApplication.scorer_id == current_user.id).all()


# ----------------------------------------------------
# 7. Notifications Logs
# ----------------------------------------------------

@api_router.get("/notifications/logs", response_model=List[schemas.NotificationLogOut])
def get_notification_logs(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Exposes all sent system emails for simple POC validation."""
    return crud.get_notifications(db)


# ----------------------------------------------------
# 8. POC DB Seeding Endpoint
# ----------------------------------------------------

@api_router.post("/seed")
def seed_database(db: Session = Depends(deps.get_db)):
    """Seeds the initial Super Admin, Department, and Federation for ease of testing."""
    # 1. Create Super Admin
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
        
    # 2. Create default Department
    dept = db.query(Department).first()
    if not dept:
        dept = Department(
            name="National Cricket Council",
            created_by_id=super_admin.id
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        
    # 3. Create Department Admin
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
        
    # 4. Create default Federation Admin user
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
        
    # 5. Create default Federation
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

    # 6. Create some sample Users for easier play
    # Players
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

    # Add players to Team Players
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

    db.commit()

    return {"status": "success", "message": "Database seeded with complete set of Tournaments, Teams, Live Matches, and Mailbox Logs (password123 for all)."}
