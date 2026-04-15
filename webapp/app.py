from collections import defaultdict
import random
import hashlib
import subprocess
# --- Required imports for dataclasses, typing, FastAPI, and dependencies ---
from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import secrets
import string
import sys
import time
import csv
import io
import zipfile
import sqlite3
from datetime import datetime, timezone
from threading import Lock


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_room_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def make_token() -> str:
    return secrets.token_urlsafe(24)


@dataclass
class Visitor:
    name: str
    role: Literal["player", "spectator"]
    client_id: str | None = None
    joined_at: str = field(default_factory=utc_now)
    team: str | None = None  # New: team name


@dataclass
class Lobby:
    code: str
    admin_name: str
    admin_token: str
    created_at: str = field(default_factory=utc_now)
    lobby_status: Literal["waiting", "live", "ended"] = "waiting"
    started_at: str | None = None
    ended_at: str | None = None
    visitors: list[Visitor] = field(default_factory=list)
    join_requests: list["JoinRequest"] = field(default_factory=list)


@dataclass
class JoinRequest:
    request_id: str
    name: str
    role: Literal["player", "spectator"]
    client_id: str | None = None
    requested_at: str = field(default_factory=utc_now)
    status: Literal["pending", "approved", "denied"] = "pending"
    decided_at: str | None = None
    team: str | None = None  # New: team name


class CreateLobbyRequest(BaseModel):
    admin_name: str = Field(min_length=1, max_length=40)


class CreateLobbyResponse(BaseModel):
    room_code: str
    admin_token: str


class JoinLobbyRequest(BaseModel):
    room_code: str = Field(min_length=4, max_length=8)
    name: str = Field(min_length=1, max_length=40)
    role: Literal["player", "spectator"] = "player"
    client_id: str | None = Field(default=None, max_length=64)
    team: str | None = Field(default=None, max_length=32)  # New: team name


class PublicStats(BaseModel):
    room_code: str
    lobby_status: Literal["waiting", "live", "ended"]
    started_at: str | None = None
    ended_at: str | None = None
    total_visitors: int
    players: int
    spectators: int


class AdminStats(PublicStats):
    admin_name: str
    created_at: str
    visitors: list[dict[str, str]]
    pending_join_requests: int = 0


class LobbyJoinRequestView(BaseModel):
    request_id: str
    name: str
    role: Literal["player", "spectator"]
    client_id: str | None = None
    requested_at: str
    status: Literal["pending", "approved", "denied"]
    decided_at: str | None = None
    team: str | None = None  # New: team name


class JoinLobbyResponse(BaseModel):
    status: Literal["joined", "pending"]
    message: str
    stats: PublicStats | None = None
    request_id: str | None = None
    team: str | None = None  # New: team name


class JoinRequestStatusResponse(BaseModel):
    status: Literal["pending", "approved", "denied", "not-found"]
    request_id: str
    room_code: str
    message: str


class GameLevel(BaseModel):
    id: str
    title: str
    points: int
    description: str
    difficulty_tier: str
    required_solved: int = 0
    unlock_hint: str | None = None
    unlocked: bool | None = None


class GameLevelDetail(BaseModel):
    id: str
    title: str
    points: int
    description: str
    difficulty_tier: str
    required_solved: int
    unlock_hint: str | None = None
    challenge_prompt: str
    challenge_token: str


class SubmitAnswerRequest(BaseModel):
    level_id: str = Field(min_length=1, max_length=20)
    answer: str = Field(min_length=1, max_length=200)
    challenge_token: str = Field(min_length=8, max_length=128)
    client_id: str | None = Field(default=None, max_length=64)
    player_name: str | None = Field(default=None, max_length=40)
    room_code: str | None = Field(default=None, max_length=8)
    solve_seconds: float | None = Field(default=None, ge=0.0, le=1800.0)


class SubmitAnswerResponse(BaseModel):
    level_id: str
    correct: bool
    points: int
    message: str
    base_points: int = 0
    bonus_points: int = 0
    difficulty_tier: str | None = None
    streak_count: int = 0
    blocked: bool = False
    attempts_left: int | None = None
    cooldown_remaining_seconds: int | None = None


class DoomdadaStatusResponse(BaseModel):
    blocked: bool
    attempts_left: int
    cooldown_remaining_seconds: int


class SessionHeartbeatRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=64)
    player_name: str = Field(min_length=1, max_length=40)
    room_code: str | None = Field(default=None, max_length=8)


class ClassroomPlayerSummary(BaseModel):
    client_id: str
    player_name: str
    score: int
    solved_count: int
    solved_levels: list[str]
    total_submissions: int
    correct_submissions: int
    current_streak: int
    best_streak: int
    accuracy: float
    last_level_id: str | None = None
    last_activity: str | None = None
    team: str | None = None  # New: team name


class ClassroomSummaryResponse(BaseModel):
    generated_at: str
    active_players: int
    total_submissions: int
    total_solves: int
    players: list[ClassroomPlayerSummary]


class PublicLeaderboardEntry(BaseModel):
    rank: int
    player_name: str
    score: int
    solved_count: int
    accuracy: float
    team: str | None = None  # New: team name


class ScoringRuleLevel(BaseModel):
    level_id: str
    title: str
    difficulty_tier: str
    base_points: int
    speed_target_seconds: float
    speed_points_per_second: float
    speed_bonus_cap_percent: float


class ScoringRulesResponse(BaseModel):
    base_rule: str
    tier_bonus_rule: str
    streak_bonus_rule: str
    speed_bonus_rule: str
    streak_bonus_cap_percent: float
    levels: list[ScoringRuleLevel]


class LevelAnalyticsItem(BaseModel):
    level_id: str
    title: str
    difficulty_tier: str
    total_submissions: int
    correct_submissions: int
    fail_rate_percent: float
    avg_solve_seconds: float | None = None
    speed_target_seconds: float
    pace_delta_seconds: float | None = None
    recommendation: str


class ClassroomLevelAnalyticsResponse(BaseModel):
    generated_at: str
    room_code: str
    levels: list[LevelAnalyticsItem]


class SessionReportTopPlayer(BaseModel):
    rank: int
    player_name: str
    score: int
    solved_count: int
    accuracy: float
    best_streak: int


class SessionReportResponse(BaseModel):
    generated_at: str
    room_code: str
    lobby_status: Literal["waiting", "live", "ended"]
    total_players: int
    total_submissions: int
    total_solves: int
    average_score: float
    average_accuracy: float
    average_completion_percent: float
    top_performers: list[SessionReportTopPlayer]
    best_accuracy_player: str | None = None
    hardest_level: str | None = None
    slowest_level: str | None = None
    highlights: list[str]


@dataclass
class PlayerProgress:
    solved_levels: set[str] = field(default_factory=set)
    current_streak: int = 0
    best_streak: int = 0


@dataclass
class DoomdadaClientState:
    attempts_left: int = 3
    cooldown_until: float = 0.0


class GameProgressStore:
    def __init__(self, db_path: Path) -> None:
        self._lock = Lock()
        self._db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    client_id TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL DEFAULT 'GLOBAL',
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL DEFAULT 0,
                    total_submissions INTEGER NOT NULL DEFAULT 0,
                    correct_submissions INTEGER NOT NULL DEFAULT 0,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    best_streak INTEGER NOT NULL DEFAULT 0,
                    last_level_id TEXT,
                    last_activity TEXT,
                    team TEXT
                );

                CREATE TABLE IF NOT EXISTS solved_levels (
                    client_id TEXT NOT NULL,
                    room_code TEXT NOT NULL DEFAULT 'GLOBAL',
                    level_id TEXT NOT NULL,
                    solved_at TEXT NOT NULL,
                    PRIMARY KEY (client_id, level_id)
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    room_code TEXT NOT NULL DEFAULT 'GLOBAL',
                    player_name TEXT NOT NULL,
                    level_id TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    points INTEGER NOT NULL,
                    solve_seconds REAL,
                    submitted_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "players", "room_code", "TEXT NOT NULL DEFAULT 'GLOBAL'")
            self._ensure_column(conn, "players", "current_streak", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "players", "best_streak", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "players", "team", "TEXT")
            self._ensure_column(conn, "solved_levels", "room_code", "TEXT NOT NULL DEFAULT 'GLOBAL'")
            self._ensure_column(conn, "submissions", "room_code", "TEXT NOT NULL DEFAULT 'GLOBAL'")
            self._ensure_column(conn, "submissions", "solve_seconds", "REAL")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(row[1] == column for row in rows):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _room(self, room_code: str | None) -> str:
        value = (room_code or "GLOBAL").strip().upper()
        if not value:
            return "GLOBAL"
        return value[:8]

    def _key(self, client_id: str | None, room_code: str | None = None) -> str:
        value = (client_id or "anonymous").strip()
        if not value:
            value = "anonymous"
        room = self._room(room_code)
        return f"{room}:{value[:64]}"

    def _display_name(self, player_name: str | None) -> str:
        value = (player_name or "").strip()
        return value[:40] if value else "Anonymous"

    def heartbeat(self, client_id: str, player_name: str, room_code: str | None = None) -> None:
        room = self._room(room_code)
        key = self._key(client_id, room)
        display_name = self._display_name(player_name)
        now = utc_now()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO players (
                        client_id, room_code, player_name, score, total_submissions, correct_submissions, current_streak, best_streak, last_level_id, last_activity
                    ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, NULL, ?)
                    ON CONFLICT(client_id) DO UPDATE SET
                        room_code = excluded.room_code,
                        player_name = CASE
                            WHEN excluded.player_name <> 'Anonymous' THEN excluded.player_name
                            ELSE players.player_name
                        END,
                        last_activity = excluded.last_activity
                    """,
                    (key, room, display_name, now),
                )

    def record_submission(
        self,
        *,
        client_id: str | None,
        player_name: str | None,
        room_code: str | None,
        level_id: str,
        correct: bool,
        points: int,
        solve_seconds: float | None = None,
    ) -> None:
        room = self._room(room_code)
        key = self._key(client_id, room)
        display_name = self._display_name(player_name)
        now = utc_now()
        point_value = max(0, points)
        correct_value = 1 if correct else 0

        with self._lock:
            with self._connect() as conn:
                previous = conn.execute(
                    """
                    SELECT current_streak, best_streak
                    FROM players
                    WHERE client_id = ?
                    """,
                    (key,),
                ).fetchone()
                prior_streak = int(previous["current_streak"] or 0) if previous else 0
                prior_best = int(previous["best_streak"] or 0) if previous else 0
                next_streak = prior_streak + 1 if correct else 0
                next_best = max(prior_best, next_streak)

                conn.execute(
                    """
                    INSERT INTO submissions (
                        client_id, room_code, player_name, level_id, correct, points, solve_seconds, submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        room,
                        display_name,
                        level_id,
                        correct_value,
                        point_value if correct else 0,
                        solve_seconds,
                        now,
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO players (
                        client_id, room_code, player_name, score, total_submissions, correct_submissions, current_streak, best_streak, last_level_id, last_activity
                    ) VALUES (?, ?, ?, 0, 1, ?, ?, ?, ?, ?)
                    ON CONFLICT(client_id) DO UPDATE SET
                        room_code = excluded.room_code,
                        player_name = CASE
                            WHEN excluded.player_name <> 'Anonymous' THEN excluded.player_name
                            ELSE players.player_name
                        END,
                        total_submissions = players.total_submissions + 1,
                        correct_submissions = players.correct_submissions + excluded.correct_submissions,
                        current_streak = excluded.current_streak,
                        best_streak = max(players.best_streak, excluded.best_streak),
                        last_level_id = excluded.last_level_id,
                        last_activity = excluded.last_activity
                    """,
                    (key, room, display_name, correct_value, next_streak, next_best, level_id, now),
                )

                if correct:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO solved_levels (client_id, room_code, level_id, solved_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (key, room, level_id, now),
                    )
                    if cursor.rowcount:
                        conn.execute(
                            "UPDATE players SET score = score + ? WHERE client_id = ?",
                            (point_value, key),
                        )

    def player_progress(self, client_id: str | None, room_code: str | None) -> PlayerProgress:
        room = self._room(room_code)
        key = self._key(client_id, room)
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT current_streak, best_streak
                    FROM players
                    WHERE client_id = ?
                    """,
                    (key,),
                ).fetchone()
                solved_rows = conn.execute(
                    """
                    SELECT level_id
                    FROM solved_levels
                    WHERE client_id = ?
                    AND room_code = ?
                    """,
                    (key, room),
                ).fetchall()
                solved = {item["level_id"] for item in solved_rows}
                return PlayerProgress(
                    solved_levels=solved,
                    current_streak=int(row["current_streak"] or 0) if row else 0,
                    best_streak=int(row["best_streak"] or 0) if row else 0,
                )

    def summary(self, room_code: str | None) -> ClassroomSummaryResponse:
        room = self._room(room_code)
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT client_id, player_name, score, total_submissions, correct_submissions, last_level_id, last_activity
                    FROM players
                    WHERE room_code = ?
                    ORDER BY score DESC, correct_submissions DESC, lower(player_name) ASC
                    """
                    ,
                    (room,),
                ).fetchall()

                payload: list[ClassroomPlayerSummary] = []
                total_submissions = 0
                total_solves = 0

                for row in rows:
                    solved_rows = conn.execute(
                        """
                        SELECT level_id FROM solved_levels
                        WHERE client_id = ?
                        AND room_code = ?
                        ORDER BY level_id ASC
                        """,
                        (row["client_id"], room),
                    ).fetchall()
                    solved_levels = [item["level_id"] for item in solved_rows]
                    submissions_count = int(row["total_submissions"] or 0)
                    solves_count = int(row["correct_submissions"] or 0)
                    total_submissions += submissions_count
                    total_solves += solves_count

                    payload.append(
                        ClassroomPlayerSummary(
                            client_id=row["client_id"],
                            player_name=row["player_name"],
                            score=int(row["score"] or 0),
                            solved_count=len(solved_levels),
                            solved_levels=solved_levels,
                            total_submissions=submissions_count,
                            correct_submissions=solves_count,
                            current_streak=int(row["current_streak"] or 0),
                            best_streak=int(row["best_streak"] or 0),
                            accuracy=round((solves_count / submissions_count) * 100, 1) if submissions_count else 0.0,
                            last_level_id=row["last_level_id"],
                            last_activity=row["last_activity"],
                        )
                    )

            return ClassroomSummaryResponse(
                generated_at=utc_now(),
                active_players=len(payload),
                total_submissions=total_submissions,
                total_solves=total_solves,
                players=payload,
            )

    def export_csv(self, room_code: str | None) -> str:
        summary = self.summary(room_code)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "player_name",
            "score",
            "solved_count",
            "solved_levels",
            "accuracy_percent",
            "correct_submissions",
            "total_submissions",
            "current_streak",
            "best_streak",
            "last_level_id",
            "last_activity",
            "client_id",
        ])
        for player in summary.players:
            writer.writerow([
                player.player_name,
                player.score,
                player.solved_count,
                "|".join(player.solved_levels),
                player.accuracy,
                player.correct_submissions,
                player.total_submissions,
                player.current_streak,
                player.best_streak,
                player.last_level_id or "",
                player.last_activity or "",
                player.client_id,
            ])
        return buffer.getvalue()

    def level_analytics(self, room_code: str | None) -> dict[str, dict[str, float | int | None]]:
        room = self._room(room_code)
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        level_id,
                        COUNT(*) AS total_submissions,
                        SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct_submissions,
                        AVG(CASE WHEN correct = 1 AND solve_seconds IS NOT NULL AND solve_seconds > 0 THEN solve_seconds END) AS avg_solve_seconds
                    FROM submissions
                    WHERE room_code = ?
                    GROUP BY level_id
                    """,
                    (room,),
                ).fetchall()

                payload: dict[str, dict[str, float | int | None]] = {}
                for row in rows:
                    payload[row["level_id"]] = {
                        "total_submissions": int(row["total_submissions"] or 0),
                        "correct_submissions": int(row["correct_submissions"] or 0),
                        "avg_solve_seconds": float(row["avg_solve_seconds"]) if row["avg_solve_seconds"] is not None else None,
                    }
                return payload


class ChallengeTicketGuard:
    def __init__(self, ttl_seconds: float = 180.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._tickets: dict[str, tuple[str, float]] = {}

    def _key(self, client_id: str | None, level_id: str) -> str:
        ident = (client_id or "anonymous").strip() or "anonymous"
        return f"{ident[:64]}:{level_id}"

    def issue(self, client_id: str | None, level_id: str) -> str:
        token = secrets.token_urlsafe(24)
        expiry = time.time() + self._ttl_seconds
        key = self._key(client_id, level_id)
        with self._lock:
            self._tickets[key] = (token, expiry)
        return token

    def validate(self, client_id: str | None, level_id: str, token: str) -> bool:
        key = self._key(client_id, level_id)
        now = time.time()
        with self._lock:
            current = self._tickets.get(key)
            if not current:
                return False
            expected, expiry = current
            if expiry < now:
                del self._tickets[key]
                return False
            return secrets.compare_digest(expected, token)


class DoomdadaGuard:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[str, DoomdadaClientState] = {}

    def _key(self, client_id: str | None) -> str:
        value = (client_id or "anonymous").strip()
        if not value:
            return "anonymous"
        return value[:64]

    def _state(self, key: str) -> DoomdadaClientState:
        state = self._states.get(key)
        if state is None:
            state = DoomdadaClientState()
            self._states[key] = state
        return state

    def status(self, client_id: str | None) -> DoomdadaStatusResponse:
        key = self._key(client_id)
        with self._lock:
            state = self._state(key)
            now = time.time()
            if state.cooldown_until <= now and state.attempts_left == 0:
                state.attempts_left = 3
                state.cooldown_until = 0.0

            remaining = max(0, int(state.cooldown_until - now + 0.999))
            blocked = remaining > 0
            return DoomdadaStatusResponse(
                blocked=blocked,
                attempts_left=state.attempts_left,
                cooldown_remaining_seconds=remaining,
            )

    def mark_success(self, client_id: str | None) -> DoomdadaStatusResponse:
        key = self._key(client_id)
        with self._lock:
            state = self._state(key)
            state.attempts_left = 3
            state.cooldown_until = 0.0
        return self.status(client_id)

    def mark_failure(self, client_id: str | None) -> DoomdadaStatusResponse:
        key = self._key(client_id)
        with self._lock:
            state = self._state(key)
            now = time.time()
            if state.cooldown_until > now:
                remaining = max(0, int(state.cooldown_until - now + 0.999))
                return DoomdadaStatusResponse(blocked=True, attempts_left=0, cooldown_remaining_seconds=remaining)

            state.attempts_left = max(0, state.attempts_left - 1)
            if state.attempts_left == 0:
                state.cooldown_until = now + 60.0

        return self.status(client_id)


GAME_LEVELS: list[GameLevel] = [
    GameLevel(id="easy", title="Easy", points=50, description="Bridge Note - Warm-up Word", difficulty_tier="easy", required_solved=0),
    GameLevel(id="medium", title="Medium", points=100, description="Earl's Tag - EARLYBIRD Cipher", difficulty_tier="medium", required_solved=0),
    GameLevel(id="mediumplus1", title="Medium+ 1", points=125, description="Split and Rebuild - Ordered Packet", difficulty_tier="medium-plus", required_solved=0),
    GameLevel(id="mediumplus2", title="Medium+ 2", points=140, description="Layered Transform - Reverse and Replace", difficulty_tier="medium-plus", required_solved=0),
    GameLevel(id="hard", title="Hard", points=150, description="Mask Pattern - Case Control", difficulty_tier="hard", required_solved=0),
    GameLevel(id="xhard", title="XHARD", points=200, description="Block Hunt - Story Clue Puzzle", difficulty_tier="very-hard", required_solved=0),
    GameLevel(id="crazy", title="CRAZY", points=250, description="Reaction Core - Precision Timing", difficulty_tier="insane", required_solved=0),
    GameLevel(id="doomdada", title="DOOMDADA", points=300, description="Final Boss Story Script", difficulty_tier="elite", required_solved=0),
]

LEVEL_BY_ID: dict[str, GameLevel] = {level.id: level for level in GAME_LEVELS}

DIFFICULTY_BONUS: dict[str, int] = {
    "easy": 0,
    "medium": 10,
    "medium-plus": 20,
    "hard": 35,
    "very-hard": 45,
    "insane": 60,
    "elite": 75,
}

LEVEL_SPEED_TARGETS: dict[str, float] = {
    "easy": 45.0,
    "medium": 60.0,
    "mediumplus1": 75.0,
    "mediumplus2": 80.0,
    "hard": 90.0,
    "xhard": 120.0,
    "crazy": 25.0,
    "doomdada": 180.0,
}

SPEED_BONUS_SETTINGS: dict[str, dict[str, float]] = {
    "easy": {"points_per_second": 1.0, "max_percent": 0.30},
    "medium": {"points_per_second": 1.2, "max_percent": 0.35},
    "mediumplus1": {"points_per_second": 1.3, "max_percent": 0.40},
    "mediumplus2": {"points_per_second": 1.35, "max_percent": 0.40},
    "hard": {"points_per_second": 1.5, "max_percent": 0.45},
    "xhard": {"points_per_second": 1.6, "max_percent": 0.50},
    "crazy": {"points_per_second": 2.0, "max_percent": 0.35},
    "doomdada": {"points_per_second": 1.4, "max_percent": 0.55},
}

STREAK_BONUS_CAP_PERCENT = 0.50

CASE_SENSITIVE_LEVELS: set[str] = {"hard", "doomdada"}

GAME_LEVEL_PROMPTS: dict[str, str] = {
    "easy": "Unscramble PMTOOCBA and submit with format DOOM{WORD}.",
    "medium": "Start from EARLYBIRD. Apply E->3 and I->1. Submit with exact inner quotes.",
    "mediumplus1": "Packet shards: C3-BOOT-AMP. Reorder by index [2,3,1], join with underscores, then wrap with DOOM{...}.",
    "mediumplus2": "Start from RUNTIME. Step 1 reverse text. Step 2 replace E->3, I->1, T->7. Step 3 append ! and submit in DOOM{...}.",
    "hard": "Start from ambatukammm. Capitalize positions #1, #3, #6 (1-based). Submit with exact inner quotes.",
    "xhard": "Reconstruct the hidden phrase from clue fragments. Submit the final flag in DOOM{...} format.",
    "crazy": "Reaction challenge target: submit the calibration flag for 6.7s mastery.",
    "doomdada": "Trace the final boss transformations and submit exact symbols and casing.",
}

# Keep answer validation server-side so clients only receive pass/fail + points.
GAME_ANSWER_KEY: dict[str, str] = {
    "easy": "DOOM{BOOTCAMP}",
    "medium": 'DOOM{"3ARLYB1RD"}',
    "mediumplus1": "DOOM{BOOT_AMP_C3}",
    "mediumplus2": "DOOM{3M17NUR!}",
    "hard": 'DOOM{"AmBatUkammm"}',
    "xhard": "DOOM{WE_7HE_B3ST}",
    "crazy": "DOOM{6.7_MASTER}",
    "doomdada": "DOOM{C0n6r@+Ul4tIoN$!}",
}


class LobbyStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._lobbies: dict[str, Lobby] = {}

    def create_lobby(self, admin_name: str) -> Lobby:
        with self._lock:
            # Retry until unique code is generated.
            for _ in range(20):
                code = make_room_code()
                if code not in self._lobbies:
                    lobby = Lobby(code=code, admin_name=admin_name.strip(), admin_token=make_token())
                    self._lobbies[code] = lobby
                    return lobby
            raise RuntimeError("Failed to generate unique room code")

    def get_lobby(self, room_code: str) -> Lobby:
        code = room_code.upper().strip()
        lobby = self._lobbies.get(code)
        if not lobby:
            raise KeyError(code)
        return lobby

    def _normalize_client_id(self, client_id: str | None) -> str | None:
        value = (client_id or "").strip()
        return value[:64] if value else None

    def _find_visitor(
        self,
        lobby: Lobby,
        name: str,
        role: Literal["player", "spectator"],
    ) -> Visitor | None:
        target = name.strip().lower()
        for visitor in lobby.visitors:
            if visitor.role != role:
                continue
            if visitor.name.strip().lower() == target:
                return visitor
        return None

    def _find_pending_request(
        self,
        lobby: Lobby,
        name: str,
        role: Literal["player", "spectator"],
        client_id: str | None,
    ) -> JoinRequest | None:
        target_name = name.strip().lower()
        for request in lobby.join_requests:
            if request.role != role:
                continue
            if request.name.strip().lower() != target_name:
                continue
            if (request.client_id or "") != (client_id or ""):
                continue
            return request
        return None

    def join_lobby(
        self,
        room_code: str,
        name: str,
        role: Literal["player", "spectator"],
        client_id: str | None = None,
        team: str | None = None,
    ) -> tuple[Literal["joined", "pending"], Lobby, str | None, str | None]:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if lobby.lobby_status == "ended":
                raise RuntimeError("lobby-ended")
            display_name = name.strip()
            normalized_client = self._normalize_client_id(client_id)
            team_name = (team or "").strip() or None
            existing = self._find_visitor(lobby, display_name, role)

            if existing:
                if existing.client_id and normalized_client and existing.client_id != normalized_client:
                    raise ValueError("name-taken")
                if existing.client_id is None and normalized_client:
                    existing.client_id = normalized_client
                return ("joined", lobby, None, existing.team)

            if lobby.lobby_status == "live":
                # Allow reconnect requests after game start, but require admin approval for brand-new players.
                pending = self._find_pending_request(lobby, display_name, role, normalized_client)
                if pending:
                    if pending.status == "pending":
                        return ("pending", lobby, pending.request_id, pending.team)
                    if pending.status == "approved":
                        lobby.visitors.append(
                            Visitor(name=display_name, role=role, client_id=normalized_client, team=pending.team)
                        )
                        return ("joined", lobby, None, pending.team)
                    # If denied, create a fresh request so player can re-request.

                request = JoinRequest(
                    request_id=make_token(),
                    name=display_name,
                    role=role,
                    client_id=normalized_client,
                    team=team_name,
                )
                lobby.join_requests.append(request)
                return ("pending", lobby, request.request_id, team_name)

            if any(v.name.lower() == display_name.lower() for v in lobby.visitors):
                raise ValueError("name-taken")
            lobby.visitors.append(Visitor(name=display_name, role=role, client_id=normalized_client, team=team_name))
            return ("joined", lobby, None, team_name)

    def is_joined_player(self, room_code: str, name: str, client_id: str | None) -> bool:
        lobby = self.get_lobby(room_code)
        target_name = name.strip().lower()
        normalized_client = self._normalize_client_id(client_id)

        for visitor in lobby.visitors:
            if visitor.role != "player":
                continue
            if visitor.name.strip().lower() != target_name:
                continue
            if visitor.client_id and normalized_client and visitor.client_id != normalized_client:
                return False
            return True

        return False

    def start_game(self, room_code: str, admin_token: str) -> Lobby:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if admin_token != lobby.admin_token:
                raise PermissionError("bad-token")
            if lobby.lobby_status == "ended":
                raise RuntimeError("already-ended")
            if lobby.lobby_status != "live":
                lobby.lobby_status = "live"
                lobby.started_at = utc_now()
                lobby.ended_at = None
            return lobby

    def stop_game(self, room_code: str, admin_token: str) -> Lobby:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if admin_token != lobby.admin_token:
                raise PermissionError("bad-token")
            if lobby.lobby_status == "waiting":
                raise RuntimeError("not-started")
            if lobby.lobby_status != "ended":
                lobby.lobby_status = "ended"
                lobby.ended_at = utc_now()
            return lobby

    def list_join_requests(self, room_code: str, admin_token: str) -> list[LobbyJoinRequestView]:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if admin_token != lobby.admin_token:
                raise PermissionError("bad-token")

            return [
                LobbyJoinRequestView(
                    request_id=req.request_id,
                    name=req.name,
                    role=req.role,
                    client_id=req.client_id,
                    requested_at=req.requested_at,
                    status=req.status,
                    decided_at=req.decided_at,
                )
                for req in sorted(lobby.join_requests, key=lambda item: item.requested_at, reverse=True)
            ]

    def decide_join_request(
        self,
        room_code: str,
        request_id: str,
        approve: bool,
        admin_token: str,
    ) -> LobbyJoinRequestView:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if admin_token != lobby.admin_token:
                raise PermissionError("bad-token")

            for req in lobby.join_requests:
                if req.request_id != request_id:
                    continue
                req.status = "approved" if approve else "denied"
                req.decided_at = utc_now()

                if approve and not self._find_visitor(lobby, req.name, req.role):
                    lobby.visitors.append(
                        Visitor(name=req.name, role=req.role, client_id=req.client_id)
                    )

                return LobbyJoinRequestView(
                    request_id=req.request_id,
                    name=req.name,
                    role=req.role,
                    client_id=req.client_id,
                    requested_at=req.requested_at,
                    status=req.status,
                    decided_at=req.decided_at,
                )

            raise KeyError(request_id)

    def join_request_status(self, room_code: str, request_id: str) -> JoinRequestStatusResponse:
        with self._lock:
            lobby = self.get_lobby(room_code)
            for req in lobby.join_requests:
                if req.request_id != request_id:
                    continue
                message = "Awaiting admin approval"
                if req.status == "approved":
                    message = "Approved by admin"
                elif req.status == "denied":
                    message = "Denied by admin"
                return JoinRequestStatusResponse(
                    status=req.status,
                    request_id=req.request_id,
                    room_code=lobby.code,
                    message=message,
                )
            return JoinRequestStatusResponse(
                status="not-found",
                request_id=request_id,
                room_code=lobby.code,
                message="Join request not found",
            )

    def public_stats(self, room_code: str) -> PublicStats:
        lobby = self.get_lobby(room_code)
        players = sum(1 for v in lobby.visitors if v.role == "player")
        spectators = sum(1 for v in lobby.visitors if v.role == "spectator")
        return PublicStats(
            room_code=lobby.code,
            lobby_status=lobby.lobby_status,
            started_at=lobby.started_at,
            ended_at=lobby.ended_at,
            total_visitors=len(lobby.visitors),
            players=players,
            spectators=spectators,
        )

    def admin_stats(self, room_code: str, admin_token: str) -> AdminStats:
        lobby = self.get_lobby(room_code)
        if admin_token != lobby.admin_token:
            raise PermissionError("bad-token")

        public = self.public_stats(room_code)
        visitors = [
            {"name": v.name, "role": v.role, "joined_at": v.joined_at, "team": v.team or ""}
            for v in sorted(lobby.visitors, key=lambda item: item.joined_at)
        ]

        return AdminStats(
            room_code=public.room_code,
            lobby_status=public.lobby_status,
            started_at=public.started_at,
            ended_at=public.ended_at,
            total_visitors=public.total_visitors,
            players=public.players,
            spectators=public.spectators,
            admin_name=lobby.admin_name,
            created_at=lobby.created_at,
            visitors=visitors,
            pending_join_requests=sum(1 for req in lobby.join_requests if req.status == "pending"),
        )


store = LobbyStore()
doomdada_guard = DoomdadaGuard()
challenge_ticket_guard = ChallengeTicketGuard()
progress_store = GameProgressStore(Path(__file__).resolve().parent / "game_progress.db")
app = FastAPI(title="DOOMDADA Bootcamp Lobby")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DESKTOP_GAME_PATH = BASE_DIR.parent / "reverse_engineering_game_gui.py"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_join_page() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/admin")
def serve_admin_page() -> RedirectResponse:
    return RedirectResponse(url="/static/admin.html", status_code=307)


@app.post("/api/admin/create", response_model=CreateLobbyResponse)
def create_lobby(payload: CreateLobbyRequest) -> CreateLobbyResponse:
    lobby = store.create_lobby(payload.admin_name)
    return CreateLobbyResponse(room_code=lobby.code, admin_token=lobby.admin_token)


@app.post("/api/lobby/join", response_model=JoinLobbyResponse)
def join_lobby(payload: JoinLobbyRequest) -> JoinLobbyResponse:
    try:
        join_status, _, request_id, team = store.join_lobby(
            payload.room_code, payload.name, payload.role, payload.client_id, getattr(payload, "team", None)
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except RuntimeError as exc:
        if str(exc) == "lobby-ended":
            raise HTTPException(status_code=423, detail="Game has ended. This lobby is closed.")
        raise HTTPException(status_code=423, detail="Lobby is locked.")
    except ValueError:
        raise HTTPException(status_code=409, detail="Name already used in this lobby")

    if join_status == "pending":
        return JoinLobbyResponse(
            status="pending",
            message="Join request sent. Waiting for admin approval.",
            request_id=request_id,
            team=team,
        )

    stats = store.public_stats(payload.room_code)
    return JoinLobbyResponse(status="joined", message="Joined lobby", stats=stats, team=team)


@app.get("/api/lobby/{room_code}/join-requests", response_model=list[LobbyJoinRequestView])
def list_lobby_join_requests(room_code: str, token: str) -> list[LobbyJoinRequestView]:
    try:
        return store.list_join_requests(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.post("/api/lobby/{room_code}/join-requests/{request_id}/approve", response_model=LobbyJoinRequestView)
def approve_lobby_join_request(room_code: str, request_id: str, token: str) -> LobbyJoinRequestView:
    try:
        return store.decide_join_request(room_code, request_id, True, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Join request not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.post("/api/lobby/{room_code}/join-requests/{request_id}/deny", response_model=LobbyJoinRequestView)
def deny_lobby_join_request(room_code: str, request_id: str, token: str) -> LobbyJoinRequestView:
    try:
        return store.decide_join_request(room_code, request_id, False, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Join request not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.get("/api/lobby/{room_code}/join-requests/{request_id}", response_model=JoinRequestStatusResponse)
def get_lobby_join_request_status(room_code: str, request_id: str) -> JoinRequestStatusResponse:
    try:
        return store.join_request_status(room_code, request_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")


@app.post("/api/lobby/{room_code}/start")
def start_lobby_game(room_code: str, token: str) -> dict[str, PublicStats | str]:
    try:
        store.start_game(room_code, token)
        stats = store.public_stats(room_code)
        return {
            "message": "Game started",
            "stats": stats,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except RuntimeError:
        raise HTTPException(status_code=409, detail="Game already ended for this room")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.post("/api/lobby/{room_code}/stop")
def stop_lobby_game(room_code: str, token: str) -> dict[str, PublicStats | str]:
    try:
        store.stop_game(room_code, token)
        stats = store.public_stats(room_code)
        return {
            "message": "Game stopped",
            "stats": stats,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except RuntimeError as exc:
        if str(exc) == "not-started":
            raise HTTPException(status_code=409, detail="Game has not started yet")
        raise HTTPException(status_code=409, detail="Game is already stopped")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.get("/api/lobby/{room_code}/public", response_model=PublicStats)
def get_public_lobby_stats(room_code: str) -> PublicStats:
    try:
        return store.public_stats(room_code)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")


@app.get("/api/lobby/{room_code}/admin", response_model=AdminStats)
def get_admin_lobby_stats(room_code: str, token: str) -> AdminStats:
    try:
        return store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@app.get("/api/game/levels", response_model=list[GameLevel])
def list_game_levels(client_id: str | None = None, room_code: str | None = None) -> list[GameLevel]:
    # Public metadata only; answers and validation logic remain server-side.
    progress = progress_store.player_progress(client_id, room_code)
    solved_count = len(progress.solved_levels)
    # Deterministic shuffle per player
    levels = list(GAME_LEVELS)
    if client_id:
        # Use a hash of client_id as seed for reproducibility
        seed = int(hashlib.sha256(client_id.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        rng.shuffle(levels)
    payload: list[GameLevel] = []
    for level in levels:
        unlocked = solved_count >= level.required_solved or level.id in progress.solved_levels
        unlock_hint = None
        if not unlocked:
            needed = max(0, level.required_solved - solved_count)
            unlock_hint = f"Solve {needed} more level(s) to unlock."
        payload.append(
            GameLevel(
                id=level.id,
                title=level.title,
                points=level.points,
                description=level.description,
                difficulty_tier=level.difficulty_tier,
                required_solved=level.required_solved,
                unlock_hint=unlock_hint,
                unlocked=unlocked,
            )
        )
    return payload


@app.get("/api/game/levels/{level_id}", response_model=GameLevelDetail)
def get_game_level_detail(level_id: str, client_id: str | None = None, room_code: str | None = None) -> GameLevelDetail:
    normalized = level_id.strip().lower()
    level = LEVEL_BY_ID.get(normalized)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    prompt = GAME_LEVEL_PROMPTS.get(normalized)
    if not prompt:
        raise HTTPException(status_code=404, detail="Level prompt not found")

    challenge_token = challenge_ticket_guard.issue(client_id, normalized)

    return GameLevelDetail(
        id=level.id,
        title=level.title,
        points=level.points,
        description=level.description,
        difficulty_tier=level.difficulty_tier,
        required_solved=level.required_solved,
        unlock_hint=level.unlock_hint,
        challenge_prompt=prompt,
        challenge_token=challenge_token,
    )


@app.get("/api/game/scoring-rules", response_model=ScoringRulesResponse)
def get_scoring_rules() -> ScoringRulesResponse:
    levels = []
    for level in GAME_LEVELS:
        speed = SPEED_BONUS_SETTINGS.get(level.id, {"points_per_second": 1.0, "max_percent": 0.30})
        levels.append(
            ScoringRuleLevel(
                level_id=level.id,
                title=level.title,
                difficulty_tier=level.difficulty_tier,
                base_points=level.points,
                speed_target_seconds=LEVEL_SPEED_TARGETS.get(level.id, 0.0),
                speed_points_per_second=float(speed["points_per_second"]),
                speed_bonus_cap_percent=float(speed["max_percent"]),
            )
        )

    return ScoringRulesResponse(
        base_rule="Each first-time level clear awards its base points.",
        tier_bonus_rule="Tier bonus is added based on difficulty tier.",
        streak_bonus_rule="Streak bonus grows by 10% per consecutive clear and resets on a wrong answer.",
        speed_bonus_rule="Speed bonus is awarded when solve time beats level target.",
        streak_bonus_cap_percent=STREAK_BONUS_CAP_PERCENT,
        levels=levels,
    )


@app.get("/api/game/doomdada/status", response_model=DoomdadaStatusResponse)
def get_doomdada_status(client_id: str | None = None) -> DoomdadaStatusResponse:
    return doomdada_guard.status(client_id)


@app.post("/api/game/session/heartbeat")
def register_player_session(payload: SessionHeartbeatRequest) -> dict[str, str]:
    room_code = (payload.room_code or "").strip().upper()
    if room_code:
        try:
            room = store.get_lobby(room_code)
        except KeyError:
            raise HTTPException(status_code=404, detail="Room code not found")
        if room.lobby_status == "ended":
            raise HTTPException(status_code=423, detail="Game has ended. Session updates are closed.")
        if not store.is_joined_player(room_code, payload.player_name, payload.client_id):
            raise HTTPException(status_code=403, detail="Player must join this room before activity is tracked")
    progress_store.heartbeat(payload.client_id, payload.player_name, payload.room_code)
    return {"message": "Session updated"}


@app.get("/api/game/classroom/summary", response_model=ClassroomSummaryResponse)
def get_classroom_summary(room_code: str, token: str) -> ClassroomSummaryResponse:
    try:
        store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    return progress_store.summary(room_code)


@app.get("/api/game/classroom/export.csv")
def export_classroom_csv(room_code: str, token: str) -> Response:
    try:
        store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    csv_text = progress_store.export_csv(room_code)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="classroom_progress_{room_code.upper()}.csv"'},
    )


@app.get("/api/game/classroom/leaderboard", response_model=list[PublicLeaderboardEntry])
def get_public_leaderboard(room_code: str) -> list[PublicLeaderboardEntry]:
    """Public endpoint  requires only room_code, no admin token."""
    try:
        store.get_lobby(room_code)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    summary = progress_store.summary(room_code)
    return [
        PublicLeaderboardEntry(
            rank=idx + 1,
            player_name=p.player_name,
            score=p.score,
            solved_count=p.solved_count,
            accuracy=p.accuracy,
            team=p.team,
        )
        for idx, p in enumerate(summary.players)
    ]


@app.get("/api/game/classroom/analytics", response_model=ClassroomLevelAnalyticsResponse)
def get_classroom_level_analytics(room_code: str, token: str) -> ClassroomLevelAnalyticsResponse:
    try:
        store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    raw = progress_store.level_analytics(room_code)
    items: list[LevelAnalyticsItem] = []

    for level in GAME_LEVELS:
        stats = raw.get(level.id, {})
        total = int(stats.get("total_submissions", 0) or 0)
        correct = int(stats.get("correct_submissions", 0) or 0)
        fail_rate = round(((total - correct) / total) * 100, 1) if total else 0.0
        avg_solve = stats.get("avg_solve_seconds")
        avg_solve_seconds = round(float(avg_solve), 1) if avg_solve is not None else None
        target = LEVEL_SPEED_TARGETS.get(level.id, 0.0)
        pace_delta = round(avg_solve_seconds - target, 1) if avg_solve_seconds is not None and target > 0 else None

        if total < 5:
            recommendation = "Collect more attempts for reliable balancing."
        elif fail_rate >= 70.0:
            recommendation = "Likely too hard; consider stronger hints or simpler transforms."
        elif fail_rate <= 25.0 and avg_solve_seconds is not None and avg_solve_seconds <= (target * 0.7):
            recommendation = "Likely too easy; increase puzzle complexity or reduce hints."
        elif avg_solve_seconds is not None and avg_solve_seconds > (target * 1.25):
            recommendation = "Pacing is slow; review clarity or lower time pressure."
        else:
            recommendation = "Balanced for current player sample."

        items.append(
            LevelAnalyticsItem(
                level_id=level.id,
                title=level.title,
                difficulty_tier=level.difficulty_tier,
                total_submissions=total,
                correct_submissions=correct,
                fail_rate_percent=fail_rate,
                avg_solve_seconds=avg_solve_seconds,
                speed_target_seconds=target,
                pace_delta_seconds=pace_delta,
                recommendation=recommendation,
            )
        )

    return ClassroomLevelAnalyticsResponse(
        generated_at=utc_now(),
        room_code=room_code.strip().upper(),
        levels=items,
    )


@app.get("/api/game/classroom/report", response_model=SessionReportResponse)
def get_classroom_session_report(room_code: str, token: str) -> SessionReportResponse:
    try:
        admin_stats = store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    summary = progress_store.summary(room_code)
    analytics = get_classroom_level_analytics(room_code=room_code, token=token)
    players = summary.players
    total_players = len(players)

    avg_score = round(sum(p.score for p in players) / total_players, 1) if total_players else 0.0
    avg_accuracy = round(sum(p.accuracy for p in players) / total_players, 1) if total_players else 0.0
    avg_completion = round(sum((p.solved_count / len(GAME_LEVELS)) * 100 for p in players) / total_players, 1) if total_players else 0.0

    top_performers = [
        SessionReportTopPlayer(
            rank=idx + 1,
            player_name=p.player_name,
            score=p.score,
            solved_count=p.solved_count,
            accuracy=p.accuracy,
            best_streak=p.best_streak,
        )
        for idx, p in enumerate(players[:5])
    ]

    best_accuracy = None
    if players:
        best = sorted(players, key=lambda item: (item.accuracy, item.correct_submissions, item.score), reverse=True)[0]
        best_accuracy = f"{best.player_name} ({best.accuracy}%)"

    hardest_level = None
    slowest_level = None
    if analytics.levels:
        hardest = sorted(analytics.levels, key=lambda item: item.fail_rate_percent, reverse=True)[0]
        hardest_level = f"{hardest.title} ({hardest.fail_rate_percent}% fail)"
        with_solve = [item for item in analytics.levels if item.avg_solve_seconds is not None]
        if with_solve:
            slowest = sorted(with_solve, key=lambda item: item.avg_solve_seconds or 0, reverse=True)[0]
            slowest_level = f"{slowest.title} ({slowest.avg_solve_seconds}s avg)"

    highlights: list[str] = []
    highlights.append(f"Session status: {admin_stats.lobby_status.upper()}")
    highlights.append(f"Average completion: {avg_completion}% of {len(GAME_LEVELS)} levels")
    if top_performers:
        highlights.append(f"Top scorer: {top_performers[0].player_name} with {top_performers[0].score} points")
    if best_accuracy:
        highlights.append(f"Best accuracy: {best_accuracy}")
    if hardest_level:
        highlights.append(f"Hardest level by fail rate: {hardest_level}")
    if slowest_level:
        highlights.append(f"Slowest level by pace: {slowest_level}")

    return SessionReportResponse(
        generated_at=utc_now(),
        room_code=room_code.strip().upper(),
        lobby_status=admin_stats.lobby_status,
        total_players=total_players,
        total_submissions=summary.total_submissions,
        total_solves=summary.total_solves,
        average_score=avg_score,
        average_accuracy=avg_accuracy,
        average_completion_percent=avg_completion,
        top_performers=top_performers,
        best_accuracy_player=best_accuracy,
        hardest_level=hardest_level,
        slowest_level=slowest_level,
        highlights=highlights,
    )


@app.get("/api/game/classroom/analytics.csv")
def export_classroom_analytics_csv(room_code: str, token: str) -> Response:
    analytics = get_classroom_level_analytics(room_code=room_code, token=token)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "level_id",
        "title",
        "difficulty_tier",
        "submissions",
        "correct_submissions",
        "fail_rate_percent",
        "avg_solve_seconds",
        "speed_target_seconds",
        "pace_delta_seconds",
        "recommendation",
    ])

    for item in analytics.levels:
        writer.writerow([
            item.level_id,
            item.title,
            item.difficulty_tier,
            item.total_submissions,
            item.correct_submissions,
            item.fail_rate_percent,
            "" if item.avg_solve_seconds is None else item.avg_solve_seconds,
            item.speed_target_seconds,
            "" if item.pace_delta_seconds is None else item.pace_delta_seconds,
            item.recommendation,
        ])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="classroom_analytics_{analytics.room_code}.csv"'},
    )


@app.get("/api/game/classroom/export_bundle.zip")
def export_classroom_bundle_zip(room_code: str, token: str) -> Response:
    try:
        store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    normalized_room = room_code.strip().upper()
    progress_csv = progress_store.export_csv(room_code)
    analytics = get_classroom_level_analytics(room_code=room_code, token=token)

    analytics_buffer = io.StringIO()
    analytics_writer = csv.writer(analytics_buffer)
    analytics_writer.writerow([
        "level_id",
        "title",
        "difficulty_tier",
        "submissions",
        "correct_submissions",
        "fail_rate_percent",
        "avg_solve_seconds",
        "speed_target_seconds",
        "pace_delta_seconds",
        "recommendation",
    ])
    for item in analytics.levels:
        analytics_writer.writerow([
            item.level_id,
            item.title,
            item.difficulty_tier,
            item.total_submissions,
            item.correct_submissions,
            item.fail_rate_percent,
            "" if item.avg_solve_seconds is None else item.avg_solve_seconds,
            item.speed_target_seconds,
            "" if item.pace_delta_seconds is None else item.pace_delta_seconds,
            item.recommendation,
        ])

    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"classroom_progress_{normalized_room}.csv", progress_csv)
        archive.writestr(f"classroom_analytics_{normalized_room}.csv", analytics_buffer.getvalue())

    zip_bytes.seek(0)
    return Response(
        content=zip_bytes.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="classroom_bundle_{normalized_room}.zip"'},
    )


@app.post("/api/game/submit", response_model=SubmitAnswerResponse)
def submit_game_answer(payload: SubmitAnswerRequest) -> SubmitAnswerResponse:
    room_code = (payload.room_code or "").strip().upper()
    player_name = (payload.player_name or "").strip()
    if room_code and player_name:
        try:
            room = store.get_lobby(room_code)
        except KeyError:
            raise HTTPException(status_code=404, detail="Room code not found")
        if room.lobby_status == "ended":
            raise HTTPException(status_code=423, detail="Game has ended. Submissions are closed.")
        if room.lobby_status != "live":
            raise HTTPException(status_code=423, detail="Game is not live yet.")
        if not store.is_joined_player(room_code, player_name, payload.client_id):
            raise HTTPException(status_code=403, detail="Player must join this room before submitting answers")

    level_id = payload.level_id.strip().lower()
    level = LEVEL_BY_ID.get(level_id)
    expected = GAME_ANSWER_KEY.get(level_id)
    if not level or not expected:
        raise HTTPException(status_code=404, detail="Level not found")

    if not challenge_ticket_guard.validate(payload.client_id, level_id, payload.challenge_token.strip()):
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token. Re-open the level and submit again.")

    progress = progress_store.player_progress(payload.client_id, payload.room_code)
    already_solved = level_id in progress.solved_levels

    if level_id == "doomdada":
        current = doomdada_guard.status(payload.client_id)
        if current.blocked:
            progress_store.record_submission(
                client_id=payload.client_id,
                player_name=payload.player_name,
                room_code=payload.room_code,
                level_id=level_id,
                correct=False,
                points=0,
                solve_seconds=payload.solve_seconds,
            )
            return SubmitAnswerResponse(
                level_id=level_id,
                correct=False,
                points=0,
                message=f"[ BLOCK ] DOOMDADA locked for {current.cooldown_remaining_seconds}s.",
                difficulty_tier=level.difficulty_tier,
                streak_count=progress.current_streak,
                blocked=True,
                attempts_left=current.attempts_left,
                cooldown_remaining_seconds=current.cooldown_remaining_seconds,
            )

    candidate = payload.answer.strip()
    expected_value = expected.strip()
    if level_id in CASE_SENSITIVE_LEVELS:
        is_correct = candidate == expected_value
    else:
        is_correct = candidate.upper() == expected_value.upper()

    points = 0
    base_points = 0
    bonus_points = 0
    message = "Incorrect answer. Review the challenge and try again."
    blocked = False
    attempts_left: int | None = None
    cooldown_remaining_seconds: int | None = None

    if is_correct:
        if already_solved:
            message = "Correct, but this level was already solved. No additional points awarded."
        else:
            base_points = level.points
            tier_bonus = DIFFICULTY_BONUS.get(level.difficulty_tier, 0)
            streak_bonus = int((base_points + tier_bonus) * min(STREAK_BONUS_CAP_PERCENT, progress.current_streak * 0.1))
            speed_bonus = 0
            if payload.solve_seconds is not None:
                target = LEVEL_SPEED_TARGETS.get(level_id, 0.0)
                if target > 0 and payload.solve_seconds < target:
                    speed_cfg = SPEED_BONUS_SETTINGS.get(level_id, {"points_per_second": 1.0, "max_percent": 0.30})
                    points_per_second = float(speed_cfg["points_per_second"])
                    max_percent = float(speed_cfg["max_percent"])
                    speed_bonus = int(min(base_points * max_percent, (target - payload.solve_seconds) * points_per_second))
            bonus_points = tier_bonus + streak_bonus + speed_bonus
            points = base_points + bonus_points
            message = f"Correct! +{points} points (base {base_points}, bonus {bonus_points})."
        if level_id == "doomdada":
            status = doomdada_guard.mark_success(payload.client_id)
            attempts_left = status.attempts_left
            cooldown_remaining_seconds = status.cooldown_remaining_seconds
    elif level_id == "doomdada":
        status = doomdada_guard.mark_failure(payload.client_id)
        blocked = status.blocked
        attempts_left = status.attempts_left
        cooldown_remaining_seconds = status.cooldown_remaining_seconds
        if blocked:
            message = f"[ BLOCK ] DOOMDADA locked for {cooldown_remaining_seconds}s due to repeated wrong attempts."
        else:
            message = f"Incorrect answer. Attempts remaining: {attempts_left}."

    progress_store.record_submission(
        client_id=payload.client_id,
        player_name=payload.player_name,
        room_code=payload.room_code,
        level_id=level_id,
        correct=is_correct,
        points=points,
        solve_seconds=payload.solve_seconds,
    )
    post_progress = progress_store.player_progress(payload.client_id, payload.room_code)

    return SubmitAnswerResponse(
        level_id=level_id,
        correct=is_correct,
        points=points,
        message=message,
        base_points=base_points,
        bonus_points=bonus_points,
        difficulty_tier=level.difficulty_tier,
        streak_count=post_progress.current_streak,
        blocked=blocked,
        attempts_left=attempts_left,
        cooldown_remaining_seconds=cooldown_remaining_seconds,
    )


@app.post("/api/game/launch-desktop")
def launch_desktop_game() -> dict[str, str]:
    if not DESKTOP_GAME_PATH.exists():
        raise HTTPException(status_code=404, detail="Desktop game file not found")

    try:
        subprocess.Popen(
            [sys.executable, str(DESKTOP_GAME_PATH)],
            cwd=str(DESKTOP_GAME_PATH.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except Exception as exc:  # pragma: no cover - defensive runtime path
        raise HTTPException(status_code=500, detail=f"Could not launch desktop game: {exc}")

    return {"message": "Desktop game launched"}


# --- API: Team Leaderboard ---
@app.get("/api/game/classroom/team-leaderboard", response_model=list[dict])
def get_team_leaderboard(room_code: str) -> list[dict]:
    """Returns team leaderboard for a room: team name, total score, members, etc."""
    summary = progress_store.summary(room_code)
    team_scores = defaultdict(lambda: {"score": 0, "members": [], "solves": 0})
    for p in summary.players:
        team = p.team or "No Team"
        team_scores[team]["score"] += p.score
        team_scores[team]["solves"] += p.solved_count
        team_scores[team]["members"].append(p.player_name)
    leaderboard = [
        {"team": team, "score": data["score"], "solves": data["solves"], "members": data["members"]}
        for team, data in team_scores.items()
    ]
    leaderboard.sort(key=lambda x: (-x["score"], -x["solves"], x["team"]))
    for idx, entry in enumerate(leaderboard):
        entry["rank"] = idx + 1
    return leaderboard


# Helper to render session report as Markdown
def render_session_report_markdown(report: SessionReportResponse) -> str:
    lines = []
    lines.append(f"# DOOMDADA Classroom Session Report ({report.room_code})\n")
    lines.append(f"**Status:** {report.lobby_status.upper()}  ")
    lines.append(f"**Players:** {report.total_players}  ")
    lines.append(f"**Total Submissions:** {report.total_submissions}  ")
    lines.append(f"**Total Solves:** {report.total_solves}  ")
    lines.append(f"**Average Score:** {report.average_score}\n")
    lines.append(f"**Average Accuracy:** {report.average_accuracy}%  ")
    lines.append(f"**Average Completion:** {report.average_completion_percent}%  ")
    lines.append("")
    if report.highlights:
        lines.append("## Highlights\n")
        for h in report.highlights:
            lines.append(f"- {h}")
        lines.append("")
    if report.top_performers:
        lines.append("## Top Performers\n")
        lines.append("| Rank | Player | Score | Solved | Accuracy | Best Streak |")
        lines.append("|------|--------|-------|--------|----------|-------------|")
        for p in report.top_performers:
            lines.append(f"| {p.rank} | {p.player_name} | {p.score} | {p.solved_count} | {p.accuracy}% | {p.best_streak} |")
        lines.append("")
    if report.best_accuracy_player:
        lines.append(f"**Best Accuracy:** {report.best_accuracy_player}")
    if report.hardest_level:
        lines.append(f"**Hardest Level:** {report.hardest_level}")
    if report.slowest_level:
        lines.append(f"**Slowest Level:** {report.slowest_level}")
    lines.append("")
    lines.append(f"_Generated at: {report.generated_at}_\n")
    return "\n".join(lines)


# Markdown download endpoint
@app.get("/api/game/classroom/report.md")
def get_classroom_session_report_markdown(room_code: str, token: str) -> PlainTextResponse:
    try:
        store.admin_stats(room_code, token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    report = get_classroom_session_report(room_code, token)
    md = render_session_report_markdown(report)
    filename = f"classroom_report_{room_code.strip().upper()}.md"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
