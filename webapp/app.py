from __future__ import annotations

import secrets
import sqlite3
import subprocess
import string
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


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
    joined_at: str = field(default_factory=utc_now)


@dataclass
class Lobby:
    code: str
    admin_name: str
    admin_token: str
    created_at: str = field(default_factory=utc_now)
    lobby_status: Literal["waiting", "live"] = "waiting"
    started_at: str | None = None
    visitors: list[Visitor] = field(default_factory=list)


class CreateLobbyRequest(BaseModel):
    admin_name: str = Field(min_length=1, max_length=40)


class CreateLobbyResponse(BaseModel):
    room_code: str
    admin_token: str


class JoinLobbyRequest(BaseModel):
    room_code: str = Field(min_length=4, max_length=8)
    name: str = Field(min_length=1, max_length=40)
    role: Literal["player", "spectator"] = "player"


class PublicStats(BaseModel):
    room_code: str
    lobby_status: Literal["waiting", "live"]
    started_at: str | None = None
    total_visitors: int
    players: int
    spectators: int


class AdminStats(PublicStats):
    admin_name: str
    created_at: str
    visitors: list[dict[str, str]]


class GameLevel(BaseModel):
    id: str
    title: str
    points: int
    description: str


class GameLevelDetail(BaseModel):
    id: str
    title: str
    points: int
    description: str
    challenge_prompt: str


class SubmitAnswerRequest(BaseModel):
    level_id: str = Field(min_length=1, max_length=20)
    answer: str = Field(min_length=1, max_length=200)
    client_id: str | None = Field(default=None, max_length=64)
    player_name: str | None = Field(default=None, max_length=40)


class SubmitAnswerResponse(BaseModel):
    level_id: str
    correct: bool
    points: int
    message: str
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


class ClassroomPlayerSummary(BaseModel):
    client_id: str
    player_name: str
    score: int
    solved_count: int
    solved_levels: list[str]
    total_submissions: int
    correct_submissions: int
    accuracy: float
    last_level_id: str | None = None
    last_activity: str | None = None


class ClassroomSummaryResponse(BaseModel):
    generated_at: str
    active_players: int
    total_submissions: int
    total_solves: int
    players: list[ClassroomPlayerSummary]


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
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL DEFAULT 0,
                    total_submissions INTEGER NOT NULL DEFAULT 0,
                    correct_submissions INTEGER NOT NULL DEFAULT 0,
                    last_level_id TEXT,
                    last_activity TEXT
                );

                CREATE TABLE IF NOT EXISTS solved_levels (
                    client_id TEXT NOT NULL,
                    level_id TEXT NOT NULL,
                    solved_at TEXT NOT NULL,
                    PRIMARY KEY (client_id, level_id)
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    level_id TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    points INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL
                );
                """
            )

    def _key(self, client_id: str | None) -> str:
        value = (client_id or "anonymous").strip()
        if not value:
            return "anonymous"
        return value[:64]

    def _display_name(self, player_name: str | None) -> str:
        value = (player_name or "").strip()
        return value[:40] if value else "Anonymous"

    def heartbeat(self, client_id: str, player_name: str) -> None:
        key = self._key(client_id)
        display_name = self._display_name(player_name)
        now = utc_now()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO players (
                        client_id, player_name, score, total_submissions, correct_submissions, last_level_id, last_activity
                    ) VALUES (?, ?, 0, 0, 0, NULL, ?)
                    ON CONFLICT(client_id) DO UPDATE SET
                        player_name = CASE
                            WHEN excluded.player_name <> 'Anonymous' THEN excluded.player_name
                            ELSE players.player_name
                        END,
                        last_activity = excluded.last_activity
                    """,
                    (key, display_name, now),
                )

    def record_submission(
        self,
        *,
        client_id: str | None,
        player_name: str | None,
        level_id: str,
        correct: bool,
        points: int,
    ) -> None:
        key = self._key(client_id)
        display_name = self._display_name(player_name)
        now = utc_now()
        point_value = max(0, points)
        correct_value = 1 if correct else 0

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO submissions (
                        client_id, player_name, level_id, correct, points, submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (key, display_name, level_id, correct_value, point_value if correct else 0, now),
                )

                conn.execute(
                    """
                    INSERT INTO players (
                        client_id, player_name, score, total_submissions, correct_submissions, last_level_id, last_activity
                    ) VALUES (?, ?, 0, 1, ?, ?, ?)
                    ON CONFLICT(client_id) DO UPDATE SET
                        player_name = CASE
                            WHEN excluded.player_name <> 'Anonymous' THEN excluded.player_name
                            ELSE players.player_name
                        END,
                        total_submissions = players.total_submissions + 1,
                        correct_submissions = players.correct_submissions + excluded.correct_submissions,
                        last_level_id = excluded.last_level_id,
                        last_activity = excluded.last_activity
                    """,
                    (key, display_name, correct_value, level_id, now),
                )

                if correct:
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO solved_levels (client_id, level_id, solved_at)
                        VALUES (?, ?, ?)
                        """,
                        (key, level_id, now),
                    )
                    if cursor.rowcount:
                        conn.execute(
                            "UPDATE players SET score = score + ? WHERE client_id = ?",
                            (point_value, key),
                        )

    def summary(self) -> ClassroomSummaryResponse:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT client_id, player_name, score, total_submissions, correct_submissions, last_level_id, last_activity
                    FROM players
                    ORDER BY score DESC, correct_submissions DESC, lower(player_name) ASC
                    """
                ).fetchall()

                payload: list[ClassroomPlayerSummary] = []
                total_submissions = 0
                total_solves = 0

                for row in rows:
                    solved_rows = conn.execute(
                        """
                        SELECT level_id FROM solved_levels
                        WHERE client_id = ?
                        ORDER BY level_id ASC
                        """,
                        (row["client_id"],),
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
    GameLevel(id="easy", title="Easy", points=50, description="Bridge Note - Warm-up Word"),
    GameLevel(id="medium", title="Medium", points=100, description="Earl's Tag - EARLYBIRD Cipher"),
    GameLevel(id="mediumplus1", title="Medium+ 1", points=125, description="Split and Rebuild - Ordered Packet"),
    GameLevel(id="mediumplus2", title="Medium+ 2", points=140, description="Layered Transform - Reverse and Replace"),
    GameLevel(id="hard", title="Hard", points=150, description="Mask Pattern - Case Control"),
    GameLevel(id="xhard", title="XHARD", points=200, description="Block Hunt - Story Clue Puzzle"),
    GameLevel(id="crazy", title="CRAZY", points=250, description="Reaction Core - Precision Timing"),
    GameLevel(id="doomdada", title="DOOMDADA", points=300, description="Final Boss Story Script"),
]

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

    def join_lobby(self, room_code: str, name: str, role: Literal["player", "spectator"]) -> Lobby:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if lobby.lobby_status == "live":
                raise RuntimeError("lobby-locked")
            display_name = name.strip()
            if any(v.name.lower() == display_name.lower() for v in lobby.visitors):
                raise ValueError("name-taken")
            lobby.visitors.append(Visitor(name=display_name, role=role))
            return lobby

    def start_game(self, room_code: str, admin_token: str) -> Lobby:
        with self._lock:
            lobby = self.get_lobby(room_code)
            if admin_token != lobby.admin_token:
                raise PermissionError("bad-token")
            if lobby.lobby_status != "live":
                lobby.lobby_status = "live"
                lobby.started_at = utc_now()
            return lobby

    def public_stats(self, room_code: str) -> PublicStats:
        lobby = self.get_lobby(room_code)
        players = sum(1 for v in lobby.visitors if v.role == "player")
        spectators = sum(1 for v in lobby.visitors if v.role == "spectator")
        return PublicStats(
            room_code=lobby.code,
            lobby_status=lobby.lobby_status,
            started_at=lobby.started_at,
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
            {"name": v.name, "role": v.role, "joined_at": v.joined_at}
            for v in sorted(lobby.visitors, key=lambda item: item.joined_at)
        ]

        return AdminStats(
            room_code=public.room_code,
            lobby_status=public.lobby_status,
            started_at=public.started_at,
            total_visitors=public.total_visitors,
            players=public.players,
            spectators=public.spectators,
            admin_name=lobby.admin_name,
            created_at=lobby.created_at,
            visitors=visitors,
        )


store = LobbyStore()
doomdada_guard = DoomdadaGuard()
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
    return RedirectResponse(url="/", status_code=307)


@app.post("/api/admin/create", response_model=CreateLobbyResponse)
def create_lobby(payload: CreateLobbyRequest) -> CreateLobbyResponse:
    lobby = store.create_lobby(payload.admin_name)
    return CreateLobbyResponse(room_code=lobby.code, admin_token=lobby.admin_token)


@app.post("/api/lobby/join")
def join_lobby(payload: JoinLobbyRequest) -> dict[str, str | PublicStats]:
    try:
        store.join_lobby(payload.room_code, payload.name, payload.role)
    except KeyError:
        raise HTTPException(status_code=404, detail="Room code not found")
    except RuntimeError:
        raise HTTPException(status_code=423, detail="Game already started. Lobby is locked.")
    except ValueError:
        raise HTTPException(status_code=409, detail="Name already used in this lobby")

    stats = store.public_stats(payload.room_code)
    return {
        "message": "Joined lobby",
        "stats": stats,
    }


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
def list_game_levels() -> list[GameLevel]:
    # Public metadata only; answers and validation logic remain server-side.
    return GAME_LEVELS


@app.get("/api/game/levels/{level_id}", response_model=GameLevelDetail)
def get_game_level_detail(level_id: str) -> GameLevelDetail:
    normalized = level_id.strip().lower()
    level = next((item for item in GAME_LEVELS if item.id == normalized), None)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    prompt = GAME_LEVEL_PROMPTS.get(normalized)
    if not prompt:
        raise HTTPException(status_code=404, detail="Level prompt not found")

    return GameLevelDetail(
        id=level.id,
        title=level.title,
        points=level.points,
        description=level.description,
        challenge_prompt=prompt,
    )


@app.get("/api/game/doomdada/status", response_model=DoomdadaStatusResponse)
def get_doomdada_status(client_id: str | None = None) -> DoomdadaStatusResponse:
    return doomdada_guard.status(client_id)


@app.post("/api/game/session/heartbeat")
def register_player_session(payload: SessionHeartbeatRequest) -> dict[str, str]:
    progress_store.heartbeat(payload.client_id, payload.player_name)
    return {"message": "Session updated"}


@app.get("/api/game/classroom/summary", response_model=ClassroomSummaryResponse)
def get_classroom_summary() -> ClassroomSummaryResponse:
    return progress_store.summary()


@app.post("/api/game/submit", response_model=SubmitAnswerResponse)
def submit_game_answer(payload: SubmitAnswerRequest) -> SubmitAnswerResponse:
    level_id = payload.level_id.strip().lower()
    expected = GAME_ANSWER_KEY.get(level_id)
    if not expected:
        raise HTTPException(status_code=404, detail="Level not found")

    if level_id == "doomdada":
        current = doomdada_guard.status(payload.client_id)
        if current.blocked:
            progress_store.record_submission(
                client_id=payload.client_id,
                player_name=payload.player_name,
                level_id=level_id,
                correct=False,
                points=0,
            )
            return SubmitAnswerResponse(
                level_id=level_id,
                correct=False,
                points=0,
                message=f"[ BLOCK ] DOOMDADA locked for {current.cooldown_remaining_seconds}s.",
                blocked=True,
                attempts_left=current.attempts_left,
                cooldown_remaining_seconds=current.cooldown_remaining_seconds,
            )

    is_correct = payload.answer.strip().upper() == expected.upper()
    points = 0
    message = "Incorrect answer. Review the challenge and try again."
    blocked = False
    attempts_left: int | None = None
    cooldown_remaining_seconds: int | None = None

    if is_correct:
        points = next((lvl.points for lvl in GAME_LEVELS if lvl.id == level_id), 0)
        message = f"Correct! +{points} points"
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
        level_id=level_id,
        correct=is_correct,
        points=points,
    )

    return SubmitAnswerResponse(
        level_id=level_id,
        correct=is_correct,
        points=points,
        message=message,
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
