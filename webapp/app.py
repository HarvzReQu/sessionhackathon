from __future__ import annotations

import secrets
import subprocess
import string
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


class SubmitAnswerResponse(BaseModel):
    level_id: str
    correct: bool
    points: int
    message: str


GAME_LEVELS: list[GameLevel] = [
    GameLevel(id="easy", title="Easy", points=50, description="Bridge Note - Warm-up Word"),
    GameLevel(id="medium", title="Medium", points=100, description="Earl's Tag - EARLYBIRD Cipher"),
    GameLevel(id="hard", title="Hard", points=150, description="Mask Pattern - Case Control"),
    GameLevel(id="xhard", title="XHARD", points=200, description="Block Hunt - Story Clue Puzzle"),
    GameLevel(id="crazy", title="CRAZY", points=250, description="Reaction Core - Precision Timing"),
    GameLevel(id="doomdada", title="DOOMDADA", points=300, description="Final Boss Story Script"),
]

GAME_LEVEL_PROMPTS: dict[str, str] = {
    "easy": "Unscramble PMTOOCBA and submit with format DOOM{WORD}.",
    "medium": "Start from EARLYBIRD. Apply E->3 and I->1. Submit with exact inner quotes.",
    "hard": "Start from ambatukammm. Capitalize positions #1, #3, #6 (1-based). Submit with exact inner quotes.",
    "xhard": "Reconstruct the hidden phrase from clue fragments. Submit the final flag in DOOM{...} format.",
    "crazy": "Reaction challenge target: submit the calibration flag for 6.7s mastery.",
    "doomdada": "Trace the final boss transformations and submit exact symbols and casing.",
}

# Keep answer validation server-side so clients only receive pass/fail + points.
GAME_ANSWER_KEY: dict[str, str] = {
    "easy": "DOOM{BOOTCAMP}",
    "medium": 'DOOM{"3ARLYB1RD"}',
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
def serve_admin_page() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "admin.html"))


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


@app.post("/api/game/submit", response_model=SubmitAnswerResponse)
def submit_game_answer(payload: SubmitAnswerRequest) -> SubmitAnswerResponse:
    level_id = payload.level_id.strip().lower()
    expected = GAME_ANSWER_KEY.get(level_id)
    if not expected:
        raise HTTPException(status_code=404, detail="Level not found")

    is_correct = payload.answer.strip().upper() == expected.upper()
    points = 0
    message = "Incorrect answer. Review the challenge and try again."

    if is_correct:
        points = next((lvl.points for lvl in GAME_LEVELS if lvl.id == level_id), 0)
        message = f"Correct! +{points} points"

    return SubmitAnswerResponse(
        level_id=level_id,
        correct=is_correct,
        points=points,
        message=message,
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
