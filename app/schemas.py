from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # super_admin, department_admin, federation_admin, player, coach, sponsor, scorer
    department_id: Optional[int] = None
    federation_id: Optional[int] = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_approved: bool
    department_id: Optional[int] = None
    federation_id: Optional[int] = None

    class Config:
        from_attributes = True

# Department Schemas
class DepartmentCreate(BaseModel):
    name: str

class DepartmentOut(BaseModel):
    id: int
    name: str
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True

# Federation Schemas
class FederationCreate(BaseModel):
    name: str
    admin_id: Optional[int] = None

class FederationOut(BaseModel):
    id: int
    name: str
    department_id: int
    admin_id: Optional[int] = None

    class Config:
        from_attributes = True

# Team & Registration Schemas
class TeamCreate(BaseModel):
    name: str
    coach_id: int
    player_ids: List[int]

class TeamPlayerOut(BaseModel):
    id: int
    player_id: int
    player: UserOut
    runs_scored: int
    balls_faced: int
    wickets_taken: int
    runs_conceded: int
    performance_score: float

    class Config:
        from_attributes = True

class TeamOut(BaseModel):
    id: int
    name: str
    tournament_id: int
    coach_id: Optional[int] = None
    coach: Optional[UserOut] = None
    created_by_id: Optional[int] = None
    creator: Optional[UserOut] = None
    players: List[TeamPlayerOut]
    status: str

    class Config:
        from_attributes = True

class TournamentCreate(BaseModel):
    name: str
    fee: float = 0.0
    number_of_entry: int = 8
    maximum_player_count: int = 11
    team_limits: int = 15
    overs: int = 20
    city: str
    ball_type: str
    start_date: str
    end_date: str
    timing_slots: str
    ground_name: str
    prize_pools: str
    free_or_paid: str
    registration_start_date: str
    registration_end_date: str

class TournamentOut(BaseModel):
    id: int
    name: str
    federation_id: int
    fee: float
    number_of_entry: int
    maximum_player_count: int
    team_limits: int
    overs: int
    city: Optional[str] = None
    ball_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timing_slots: Optional[str] = None
    ground_name: Optional[str] = None
    prize_pools: Optional[str] = None
    free_or_paid: Optional[str] = None
    registration_start_date: Optional[str] = None
    registration_end_date: Optional[str] = None
    is_approved: bool
    status: str
    teams: List[TeamOut] = []

    class Config:
        from_attributes = True

# Cricket Match Schemas
class MatchCreate(BaseModel):
    team_a_id: int
    team_b_id: int
    scorer_id: int

# Specific scoring events to make live scoreboard updates simple
class ScoreUpdate(BaseModel):
    team: str  # "team_a" or "team_b"
    runs: int
    wickets: int
    overs: float

class PlayerPerformanceInput(BaseModel):
    player_id: int
    runs_scored: int
    balls_faced: int
    wickets_taken: int
    runs_conceded: int

class MatchCompleteInput(BaseModel):
    winner_id: Optional[int] = None
    performances: List[PlayerPerformanceInput]

class MatchOut(BaseModel):
    id: int
    tournament_id: int
    tournament: TournamentOut
    team_a_id: int
    team_b_id: int
    team_a: TeamOut
    team_b: TeamOut
    scorer_id: Optional[int] = None
    scorer: Optional[UserOut] = None
    status: str
    team_a_runs: int
    team_a_wickets: int
    team_a_overs: float
    team_b_runs: int
    team_b_wickets: int
    team_b_overs: float
    winner_id: Optional[int] = None
    winner: Optional[TeamOut] = None

    class Config:
        from_attributes = True

# Sponsorship Schemas
class SponsorshipCreate(BaseModel):
    amount: float

class SponsorshipOut(BaseModel):
    id: int
    tournament_id: int
    sponsor_id: int
    sponsor: UserOut
    amount: float
    status: str

    class Config:
        from_attributes = True

# Notification Log Schemas
class NotificationLogOut(BaseModel):
    id: int
    recipient_email: str
    subject: str
    body: str
    sent_at: datetime

    class Config:
        from_attributes = True

# Scorer Application Schemas
class ScorerApplicationCreate(BaseModel):
    tournament_id: int

class ScorerApplicationOut(BaseModel):
    id: int
    tournament_id: int
    tournament: TournamentOut
    scorer_id: int
    scorer: UserOut
    status: str

    class Config:
        from_attributes = True

