#!/usr/bin/env python3
"""GUI version of the Reverse Engineering webinar game using tkinter."""

from __future__ import annotations

import json
import random
import io
import contextlib
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

try:
    import winsound
except ImportError:
    winsound = None


class ReverseEngineeringGameGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("VM Login")
        self.root.geometry("980x700")
        self.root.minsize(920, 640)

        self.colors = {
            "bg": "#1B1F24",
            "panel": "#242B33",
            "text": "#FFFFFF",
            "muted": "#9FB0C0",
            "accent": "#D70A53",
            "terminal": "#8AE234",
            "code_bg": "#0F1419",
            "code_text": "#C9D1D9",
        }
        self.root.configure(bg=self.colors["bg"])

        self.total_score = 0
        self.completed_levels: set[str] = set()
        self.end_credits_shown = False
        self.team_scores: dict[str, int] = {}
        self.leaderboard_path = Path(__file__).with_name("leaderboard.json")
        self.leaderboard_data = self._load_leaderboard()

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._setup_style()

        self.levels = {
            "Easy": {
                "points": 50,
                "expected": "DOOM{BOOTCAMP}",
                "desc": "Chapter 1: Bridge Note - Warm-up Word",
                "hint": "Hint: A crumpled note under the bridge has scrambled letters.",
                "learning_goal": "Spot and apply a simple text transformation rule.",
                "real_world": "Analysts often decode scrambled or obfuscated strings to understand hidden behavior.",
                "common_mistakes": [
                    "Forgetting to wrap answer in DOOM{...}",
                    "Typing the right word with wrong spelling",
                    "Adding extra spaces before or after the flag",
                ],
                "teacher_script": "We solved this by unscrambling letters, then applying the correct flag format.",
                "student_takeaway": "Break a puzzle into steps: transform first, format second.",
                "hints": [
                    "Unscramble this: PMTOOCBA.",
                    "Think of your current event theme.",
                    "The solved word is BOOTCAMP.",
                ],
                "walkthrough": (
                    "Chapter 1 Walkthrough\n\n"
                    "1) Unscramble PMTOOCBA.\n"
                    "2) You get BOOTCAMP.\n"
                    "3) Put it in flag format: DOOM{BOOTCAMP}."
                ),
                "presenter_script": (
                    "Easy Presenter Script\n\n"
                    "Chapter 1 starts with a bridge note. The letters look random, but they are only scrambled. "
                    "We rearrange PMTOOCBA into BOOTCAMP, then wrap it in our flag format."
                ),
                "content": (
                    "Story: You find a crumpled note under the bridge.\n"
                    "Mission: Decode the first keyword.\n"
                    "Puzzle: PMTOOCBA\n"
                    "Rule: Unscramble the letters, then submit as DOOM{WORD}."
                ),
            },
            "Medium": {
                "points": 100,
                "expected": 'DOOM{"3ARLYB1RD"}',
                "desc": "Chapter 2: Earl's Tag - EARLYBIRD Cipher",
                "hint": "Hint: Earl stylizes his stage tag as EARLYBIRD.",
                "learning_goal": "Practice substitution rules and precise output formatting.",
                "real_world": "Reverse engineers frequently decode text that was transformed to hide intent.",
                "common_mistakes": [
                    "Missing the inner double quotes",
                    "Only replacing one letter (E or I) instead of both",
                    "Using lowercase when uppercase is expected",
                ],
                "teacher_script": "We converted a plain word using fixed replacement rules and checked formatting precision.",
                "student_takeaway": "Small substitution rules can completely change output, so verify every character.",
                "hints": [
                    "Start from EARLYBIRD.",
                    "Replace E -> 3 and I -> 1.",
                    'Use exact custom flag: DOOM{"3ARLYB1RD"}.',
                ],
                "walkthrough": (
                    "Chapter 2 Walkthrough\n\n"
                    "1) Base phrase is EARLYBIRD.\n"
                    "2) Apply replacements: E->3, I->1.\n"
                    "3) Result becomes 3ARLYB1RD.\n"
                    "4) Wrap with quotes inside braces: DOOM{\"3ARLYB1RD\"}."
                ),
                "presenter_script": (
                    "Medium Presenter Script\n\n"
                    "Chapter 2 uses Earl's stage-name lore: EARL + Y + BIRD -> EARLYBIRD. "
                    "Then we apply gamer-style substitutions to get 3ARLYB1RD and keep exact format."
                ),
                "content": (
                    "Story: Earl leaves his signature tag near the bridge terminal.\n"
                    "Mission: Transform the tag to hacker style.\n"
                    "Base: EARLYBIRD\n"
                    "Rules: E->3, I->1\n"
                    "Then submit exactly with inner quotes."
                ),
            },
            "Hard": {
                "points": 150,
                "expected": 'DOOM{"AmBatUkammm"}',
                "desc": "Chapter 3: Mask Pattern - Case Control",
                "hint": "Hint: The bridge console logs show a strict letter-case mask.",
                "learning_goal": "Follow position-based rules accurately under constraints.",
                "real_world": "In real analysis, one wrong character can break a key, hash, or validation routine.",
                "common_mistakes": [
                    "Using 0-based indexing instead of 1-based indexing",
                    "Capitalizing the wrong letters",
                    "Forgetting the required inner quotes",
                ],
                "teacher_script": "We followed position-based capitalization exactly, then wrapped the answer correctly.",
                "student_takeaway": "In security tasks, position and case both matter; precision beats guessing.",
                "hints": [
                    "Start from: ambatukammm",
                    "Uppercase only letters #1, #3, and #6.",
                    'Use exact custom flag: DOOM{"AmBatUkammm"}.',
                ],
                "walkthrough": (
                    "Chapter 3 Walkthrough\n\n"
                    "1) Start with ambatukammm.\n"
                    "2) Uppercase positions 1, 3, and 6 (1-based indexing).\n"
                    "3) You get AmBatUkammm.\n"
                    "4) Wrap with inner quotes: DOOM{\"AmBatUkammm\"}."
                ),
                "presenter_script": (
                    "Hard Presenter Script\n\n"
                    "Chapter 3 is about precision. The console mask tells us which positions must be uppercase. "
                    "One wrong letter-case breaks the final value, just like in real validation checks."
                ),
                "content": (
                    "Story: You recover a mask rule from a hidden bridge log file.\n"
                    "Mission: Apply the letter-case mask exactly.\n"
                    "Base: ambatukammm\n"
                    "Mask (1-based): capitalize #1, #3, #6\n"
                    "Submit using exact quote format."
                ),
            },
            "XHARD": {
                "points": 200,
                "expected": "DOOM{WE_7HE_B3ST}",
                "desc": "Chapter 4: Block Hunt - Story Clue Puzzle",
                "hint": "Hint: Click block tiles to reveal the real clue fragments.",
                "learning_goal": "Collect scattered clues and reconstruct one exact flag.",
                "real_world": "Investigators combine many tiny artifacts into one final conclusion.",
                "common_mistakes": [
                    "Submitting before all clue fragments are revealed",
                    "Mixing decoy words into the final flag",
                    "Using wrong underscore placement",
                ],
                "teacher_script": "We played a clue-hunt and assembled only valid fragments in the right order.",
                "student_takeaway": "Gather evidence first, then format final output.",
                "content": (
                    "Story: You enter a ruined bridge chamber with 9 memory blocks.\n"
                    "Goal: Find the 4 true fragments hidden among decoys, then combine them into one flag.\n"
                    "Format reminder: DOOM{...}"
                ),
            },
            "CRAZY": {
                "points": 250,
                "expected": "DOOM{6.7_MASTER}",
                "desc": "Chapter 5: Reaction Core - Precision Timing",
                "hint": "Hint: Start, wait, then stop exactly at 6.7 seconds.",
                "learning_goal": "Practice precision timing under pressure.",
                "real_world": "Timing precision matters in exploit development and race-condition analysis.",
                "common_mistakes": [
                    "Stopping too early due to panic",
                    "Overshooting while waiting for perfect timing",
                    "Forgetting to retry calmly with rhythm",
                ],
                "teacher_script": "This level rewards patience and micro-precision, not speed.",
                "student_takeaway": "Control and timing can be as important as logic in security challenges.",
                "content": (
                    "Story: A reactor lock opens only when your stop timing matches 6.7 seconds.\n"
                    "Target zone: 6.7 +/- 0.07s"
                ),
            },
            "DOOMDADA": {
                "points": 300,
                "expected": "DOOM{C0n6r@+Ul4tIoN$!}",
                "desc": "Final Boss Story Script - Under The Bridge",
                "hint": "Hint: Follow each function step and keep exact symbols/casing in final output.",
                "learning_goal": "Trace a longer scripted flow and combine transformations in order.",
                "real_world": "Real reverse engineering often means reading long logic chains and reconstructing final outputs exactly.",
                "common_mistakes": [
                    "Skipping one function and jumping to final guess",
                    "Applying substitutions but forgetting exact uppercase/lowercase",
                    "Using the right phrase but wrong punctuation/symbol positions",
                ],
                "teacher_script": "We solved a long script by tracing functions one by one, then verifying exact final formatting.",
                "student_takeaway": "For hard levels, process beats intuition: follow the code path and validate every character.",
                "hints": [
                    "The story text reveals the base phrase: congratulations!",
                    "apply_leet() swaps letters: o->0, g->6, a->@, t->+, s->$",
                    "apply_case_pattern() gives: C0n6r@+Ul4tIoN$!",
                ],
                "walkthrough": (
                    "DOOMDADA Walkthrough\n\n"
                    "1) Read story_seed(): the key phrase is congratulations!\n"
                    "2) Run apply_leet(): o->0, g->6, a->@, t->+, s->$\n"
                    "3) Run apply_case_pattern(): produce C0n6r@+Ul4tIoN$!\n"
                    "4) build_flag() wraps it as DOOM{C0n6r@+Ul4tIoN$!}."
                ),
                "presenter_script": (
                    "DOOMDADA Presenter Script\n\n"
                    "This final level uses a full mini-script instead of one-liners. Students practice the real "
                    "reverse-engineering habit: inspect each function, follow data flow, and avoid skipping steps."
                ),
                "trace_table": (
                    "DOOMDADA Trace Table\n\n"
                    "phrase  = congratulations!\n"
                    "stage1  = c0n6r@+ul@+i0n$!\n"
                    "stage2  = C0n6r@+Ul4tIoN$!\n"
                    "flag    = DOOM{C0n6r@+Ul4tIoN$!}\n\n"
                    "Read it left to right: each stage applies one function from the story script."
                ),
                "content": (
                    "# DOOMDADA Final Script: Bridge Boy Cipher\n"
                    "# Story: A boy lives under the bridge and writes clues in code.\n"
                    "# Your mission is to reconstruct his final access flag.\n\n"
                    "def story_seed() -> str:\n"
                    "    \"\"\"The boy's note says: 'When they finally see me, they say this word.'\"\"\"\n"
                    "    return \"congratulations!\"\n\n"
                    "def apply_leet(text: str) -> str:\n"
                    "    # Symbol swaps from his notebook\n"
                    "    table = {\"o\": \"0\", \"g\": \"6\", \"a\": \"@\", \"t\": \"+\", \"s\": \"$\"}\n"
                    "    return \"\".join(table.get(ch, ch) for ch in text.lower())\n\n"
                    "def apply_case_pattern(text: str) -> str:\n"
                    "    # Uppercase indexes from graffiti marks (0-based): 0, 7, 8, 10, 12\n"
                    "    upper_idx = {0, 7, 8, 10, 12}\n"
                    "    out = []\n"
                    "    for i, ch in enumerate(text):\n"
                    "        out.append(ch.upper() if i in upper_idx else ch.lower())\n"
                    "    return \"\".join(out)\n\n"
                    "def build_flag() -> str:\n"
                    "    phrase = story_seed()\n"
                    "    stage1 = apply_leet(phrase)\n"
                    "    stage2 = apply_case_pattern(stage1)\n"
                    "    return f\"DOOM{{{stage2}}}\"\n\n"
                    "# QUESTION:\n"
                    "# What is the exact output of build_flag()?\n"
                    "# Submit exactly, including symbols and uppercase/lowercase."
                ),
            },
        }

        self.challenge_window: tk.Toplevel | None = None
        self.attempts_left = 0
        self.doomdada_attempts_left = 3
        self.active_level = ""
        self.timer_job: str | None = None
        self.time_left = 0
        self.side_info_box: tk.Text | None = None
        self.console_input: tk.Text | None = None
        self.console_output_var: tk.StringVar | None = None
        self.boost_mode_var = tk.BooleanVar(value=True)
        self.boost_widgets: list[tk.Widget] = []
        self.main_code_box: tk.Text | None = None
        self.main_code_job: str | None = None
        self.main_code_running = False
        self.main_bg_box: tk.Text | None = None
        self.main_bg_job: str | None = None
        self.main_bg_running = False
        self.doomdada_card_widget: tk.Widget | None = None
        self.doomdada_pulse_job: str | None = None
        self.doomdada_pulse_on = False
        self.doomdada_alert_bar: tk.Label | None = None
        self.doomdada_scan_canvas: tk.Canvas | None = None
        self.doomdada_scan_job: str | None = None
        self.doomdada_scan_x = 0
        self.startup_bg_box: tk.Text | None = None
        self.startup_bg_job: str | None = None
        self.startup_bg_running = False
        self.startup_bg_mode = "login"
        self.hint_mode_var = tk.BooleanVar(value=False)
        self.mute_sfx_var = tk.BooleanVar(value=False)
        self.level_submit_counts: dict[str, int] = {}
        self.level_hint_used: set[str] = set()
        self.level_start_time: dict[str, float] = {}
        self.level_achievements: dict[str, list[str]] = {}
        self.level_speed_targets = {
            "Easy": 45.0,
            "Medium": 60.0,
            "Hard": 75.0,
            "XHARD": 120.0,
            "CRAZY": 25.0,
            "DOOMDADA": 180.0,
        }

        self.root.update_idletasks()
        self.root.deiconify()
        self._center_root_window()
        self._build_startup_screen()
        self.root.attributes("-topmost", True)
        self.root.after(1200, lambda: self.root.attributes("-topmost", False))

    def _center_root_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width() or 980
        height = self.root.winfo_height() or 700
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _clear_root(self) -> None:
        if self.doomdada_pulse_job:
            try:
                self.root.after_cancel(self.doomdada_pulse_job)
            except Exception:
                pass
            self.doomdada_pulse_job = None
        if self.doomdada_scan_job:
            try:
                self.root.after_cancel(self.doomdada_scan_job)
            except Exception:
                pass
            self.doomdada_scan_job = None
        if self.main_bg_job:
            try:
                self.root.after_cancel(self.main_bg_job)
            except Exception:
                pass
            self.main_bg_job = None
        if self.main_code_job:
            try:
                self.root.after_cancel(self.main_code_job)
            except Exception:
                pass
            self.main_code_job = None
        if self.startup_bg_job:
            try:
                self.root.after_cancel(self.startup_bg_job)
            except Exception:
                pass
            self.startup_bg_job = None
        self.main_code_running = False
        self.main_code_box = None
        self.main_bg_running = False
        self.main_bg_box = None
        self.doomdada_card_widget = None
        self.doomdada_alert_bar = None
        self.doomdada_scan_canvas = None
        self.doomdada_scan_x = 0
        self.startup_bg_running = False
        self.startup_bg_box = None
        for widget in self.root.winfo_children():
            widget.destroy()

    def _start_startup_hacker_background(self, parent: tk.Widget, mode: str) -> None:
        self.startup_bg_mode = mode
        self.startup_bg_running = True

        self.startup_bg_box = tk.Text(
            parent,
            wrap="none",
            font=("Consolas", 9),
            bg="#06090D",
            fg="#2EA043",
            insertbackground="#2EA043",
            relief="flat",
            state="disabled",
        )
        self.startup_bg_box.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.startup_bg_box.lower()

        self._append_startup_bg_line("boot:: initializing terminal background stream")
        self._append_startup_bg_line("net:: handshake with virtual bridge node")
        self._append_startup_bg_line("enc:: 01001100 01001111 01000011 01001011")
        self._tick_startup_hacker_background()

    def _append_startup_bg_line(self, text: str) -> None:
        if self.startup_bg_box is None or not self.startup_bg_box.winfo_exists():
            return
        self.startup_bg_box.config(state="normal")
        self.startup_bg_box.insert("end", text + "\n")
        lines = int(float(self.startup_bg_box.index("end-1c").split(".")[0]))
        if lines > 260:
            self.startup_bg_box.delete("1.0", "50.0")
        self.startup_bg_box.see("end")
        self.startup_bg_box.config(state="disabled")

    def _tick_startup_hacker_background(self) -> None:
        if not self.startup_bg_running:
            self.startup_bg_job = None
            return
        if self.startup_bg_box is None or not self.startup_bg_box.winfo_exists():
            self.startup_bg_job = None
            self.startup_bg_running = False
            return

        line = self._startup_noise_line(self.startup_bg_mode)
        self._append_startup_bg_line(line)
        self.startup_bg_job = self.root.after(random.randint(70, 170), self._tick_startup_hacker_background)

    def _startup_noise_line(self, mode: str) -> str:
        # Build long lines so visible activity fills left/center/right background regions.
        binary = "".join(random.choice("01") for _ in range(24))
        ip = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        lat = random.randint(2, 120)
        code_snippets = [
            "for(i=0;i<buf_len;i++){xor[i]^=0x2A;}",
            "if(auth(user,pass)==0){grant();}",
            "token = sha256(seed + salt).hexdigest()",
            "while(socket.open()){recv(pkt);parse(pkt);}",
            "flag = f'DOOM{{{stage2}}}'",
            "try: connect(host,443); except: retry()",
        ]
        pings = [
            f"ping {ip} time={lat}ms TTL=64",
            f"icmp_seq={random.randint(1,999)} from {ip} ttl=57 time={lat}ms",
            f"nmap scan {ip} -> 22/tcp open 443/tcp open",
        ]
        actions_login = [
            "auth:: scanning credential table",
            "proc:: checking tty access",
            "sys:: awaiting operator login",
            "guard:: bruteforce shield active",
        ]
        actions_load = [
            "load:: challenge modules -> OK",
            "link:: story pipeline synced",
            "cache:: prewarming score subsystem",
            "boot:: spinning event dispatcher",
        ]
        actions_main = [
            "main:: streaming cyber backdrop",
            "main:: syncing challenge telemetry",
            "main:: rendering binary motion layer",
            "main:: operator console online",
        ]

        if mode == "loading":
            action = random.choice(actions_load)
        elif mode == "main":
            action = random.choice(actions_main)
        else:
            action = random.choice(actions_login)
        segments = [
            action,
            random.choice(code_snippets),
            random.choice(pings),
            f"bin::{binary}",
            f"hex::0x{random.randint(0, 16**8 - 1):08X}",
            f"route::{ip}/24 via 10.0.0.1",
        ]
        random.shuffle(segments)
        pad = " " * random.randint(0, 36)
        return pad + "  |  ".join(segments)

    def _start_main_screen_background(self, parent: tk.Widget) -> None:
        self.main_bg_running = True
        feed_frame = tk.Frame(parent, bg="#0A1016", highlightbackground="#1E7A47", highlightthickness=1)
        feed_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            feed_frame,
            text="LIVE BACKGROUND CODE FEED",
            font=("Consolas", 9, "bold"),
            fg="#7EE787",
            bg="#0A1016",
            anchor="w",
            padx=8,
            pady=4,
        ).pack(fill="x")

        self.main_bg_box = tk.Text(
            feed_frame,
            wrap="none",
            height=6,
            font=("Consolas", 9),
            bg="#060B11",
            fg="#4ADE80",
            insertbackground="#4ADE80",
            relief="flat",
            state="disabled",
        )
        self.main_bg_box.pack(fill="x", padx=8, pady=(0, 8))
        self._append_main_bg_line("bg:: ambient stream online")
        self._append_main_bg_line("bg:: signal boosted for stage visibility")
        self._tick_main_screen_background()

    def _append_main_bg_line(self, text: str) -> None:
        if self.main_bg_box is None or not self.main_bg_box.winfo_exists():
            return
        self.main_bg_box.config(state="normal")
        self.main_bg_box.insert("end", text + "\n")
        lines = int(float(self.main_bg_box.index("end-1c").split(".")[0]))
        if lines > 280:
            self.main_bg_box.delete("1.0", "70.0")
        self.main_bg_box.see("end")
        self.main_bg_box.config(state="disabled")

    def _tick_main_screen_background(self) -> None:
        if not self.main_bg_running:
            self.main_bg_job = None
            return
        if self.main_bg_box is None or not self.main_bg_box.winfo_exists():
            self.main_bg_job = None
            self.main_bg_running = False
            return

        binary = "".join(random.choice("01") for _ in range(18))
        line = random.choice(
            [
                f"ambient:: {binary}  ping 10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                "runner:: parse(token); validate(signature)",
                "matrix:: for ch in stream: render(ch)",
                "guard:: monitor(levels, score, attempts)",
                "trace:: stack.push(seed); transform(); finalize()",
            ]
        )
        self._append_main_bg_line(line)
        self.main_bg_job = self.root.after(random.randint(180, 360), self._tick_main_screen_background)

    def _pulse_doomdada_card(self) -> None:
        if self.doomdada_card_widget is None or not self.doomdada_card_widget.winfo_exists():
            self.doomdada_pulse_job = None
            return
        self.doomdada_pulse_on = not self.doomdada_pulse_on
        try:
            self.doomdada_card_widget.configure(
                highlightbackground="#FF4466" if self.doomdada_pulse_on else "#D70A53",
                highlightcolor="#FF4466" if self.doomdada_pulse_on else "#D70A53",
            )
        except Exception:
            pass
        self.doomdada_pulse_job = self.root.after(760, self._pulse_doomdada_card)

    def _stop_doomdada_scanline(self) -> None:
        if self.doomdada_scan_job:
            try:
                self.root.after_cancel(self.doomdada_scan_job)
            except Exception:
                pass
            self.doomdada_scan_job = None
        self.doomdada_scan_canvas = None
        self.doomdada_scan_x = 0

    def _start_doomdada_scanline(self, parent: tk.Widget) -> None:
        self._stop_doomdada_scanline()
        self.doomdada_scan_canvas = tk.Canvas(
            parent,
            height=20,
            bg="#080C10",
            highlightthickness=1,
            highlightbackground="#3B0F1F",
            relief="flat",
        )
        self.doomdada_scan_canvas.pack(fill="x", pady=(0, 8))
        self.doomdada_scan_x = 0
        self._tick_doomdada_scanline()

    def _tick_doomdada_scanline(self) -> None:
        if self.doomdada_scan_canvas is None or not self.doomdada_scan_canvas.winfo_exists():
            self.doomdada_scan_job = None
            return

        canvas = self.doomdada_scan_canvas
        width = max(10, canvas.winfo_width())
        height = max(10, canvas.winfo_height())
        canvas.delete("all")

        for y in range(2, height, 4):
            canvas.create_line(0, y, width, y, fill="#102414")

        x = self.doomdada_scan_x
        canvas.create_line(x, 0, x, height, fill="#3DDC84", width=2)
        canvas.create_line(max(0, x - 2), 0, max(0, x - 2), height, fill="#1E7A47")
        canvas.create_line(min(width, x + 2), 0, min(width, x + 2), height, fill="#1E7A47")
        canvas.create_text(
            8,
            height // 2,
            anchor="w",
            text="scanline:: signal integrity monitor",
            fill="#6EE7B7",
            font=("Consolas", 8),
        )

        self.doomdada_scan_x += 10
        if self.doomdada_scan_x > width + 6:
            self.doomdada_scan_x = -6

        self.doomdada_scan_job = self.root.after(70, self._tick_doomdada_scanline)

    def _build_startup_screen(self) -> None:
        self._clear_root()

        wrapper = tk.Frame(self.root, bg="#080C10", highlightbackground="#D70A53", highlightthickness=2)
        wrapper.pack(fill="both", expand=True, padx=18, pady=18)
        self._start_startup_hacker_background(wrapper, "login")

        # Add a subtle haze layer so foreground glow pops while keeping background animation visible.
        haze = tk.Frame(wrapper, bg="#070A0E")
        haze.place(relx=0, rely=0, relwidth=1, relheight=1)
        haze.lower()

        # Faux shadow and glow stack for center login form.
        shadow = tk.Frame(wrapper, bg="#020304")
        shadow.place(relx=0.5, rely=0.5, anchor="center", width=560, height=330, x=10, y=12)

        glow_outer = tk.Frame(wrapper, bg="#111722", highlightbackground="#2EA043", highlightthickness=1)
        glow_outer.place(relx=0.5, rely=0.5, anchor="center", width=560, height=330)

        glow_inner = tk.Frame(glow_outer, bg="#0B1118", highlightbackground="#3DDC84", highlightthickness=1)
        glow_inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.97, relheight=0.95)

        center = tk.Frame(glow_inner, bg="#080C10")
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            center,
            text="DOOMDADDY's VB",
            font=("Consolas", 22, "bold"),
            fg="#FF4477",
            bg="#080C10",
        ).pack(anchor="center", pady=(0, 8))

        tk.Label(
            center,
            text="Authenticate to launch RANDOM AHH GAME",
            font=("Consolas", 11),
            fg="#8AE234",
            bg="#080C10",
        ).pack(anchor="center", pady=(0, 20))

        tk.Label(
            center,
            text="LOGIN PAGE ACTIVE",
            font=("Consolas", 10, "bold"),
            fg="#FFD166",
            bg="#080C10",
        ).pack(anchor="center", pady=(0, 16))

        form = tk.Frame(center, bg="#080C10")
        form.pack(anchor="center")

        user_var = tk.StringVar()
        pass_var = tk.StringVar()
        status_var = tk.StringVar(value="Attempts left: 3")
        attempts = {"left": 3}

        tk.Label(form, text="Username:", font=("Consolas", 12), fg="#FFFFFF", bg="#080C10").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        user_entry = tk.Entry(
            form,
            textvariable=user_var,
            width=26,
            font=("Consolas", 12),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
        )
        user_entry.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 10))

        tk.Label(form, text="Password:", font=("Consolas", 12), fg="#FFFFFF", bg="#080C10").grid(
            row=1, column=0, sticky="w"
        )
        pass_entry = tk.Entry(
            form,
            textvariable=pass_var,
            width=26,
            font=("Consolas", 12),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
            show="*",
        )
        pass_entry.grid(row=1, column=1, sticky="w", padx=(10, 0))

        tk.Label(center, textvariable=status_var, font=("Consolas", 11), fg="#FFD166", bg="#080C10").pack(
            anchor="center", pady=(14, 14)
        )

        def do_login() -> None:
            if user_var.get().strip().upper() == "DOOM" and pass_var.get().strip().upper() == "DADA":
                self._show_startup_loading_screen()
                return

            attempts["left"] -= 1
            if attempts["left"] <= 0:
                messagebox.showerror("ACCESS DENIED", "Too many failed attempts.")
                self.root.destroy()
                return

            status_var.set(f"Attempts left: {attempts['left']}")
            messagebox.showwarning("ACCESS DENIED", "Wrong username or password.")

        actions = tk.Frame(center, bg="#080C10")
        actions.pack(anchor="center")

        tk.Button(
            actions,
            text="LOGIN",
            command=do_login,
            font=("Consolas", 11, "bold"),
            fg="#FFFFFF",
            bg="#D70A53",
            activebackground="#B70844",
            relief="flat",
            padx=14,
            pady=7,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            actions,
            text="EXIT",
            command=self.root.destroy,
            font=("Consolas", 11, "bold"),
            fg="#FFFFFF",
            bg="#374151",
            activebackground="#1F2937",
            relief="flat",
            padx=14,
            pady=7,
        ).pack(side="left")

        pass_entry.bind("<Return>", lambda _event: do_login())
        user_entry.focus_set()
        self.root.title("VM Login")

    def _show_startup_loading_screen(self) -> None:
        self._clear_root()

        frame = tk.Frame(self.root, bg="#080C10", highlightbackground="#D70A53", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        self._start_startup_hacker_background(frame, "loading")

        haze = tk.Frame(frame, bg="#070A0E")
        haze.place(relx=0, rely=0, relwidth=1, relheight=1)
        haze.lower()

        shadow = tk.Frame(frame, bg="#020304")
        shadow.place(relx=0.5, rely=0.5, anchor="center", width=760, height=190, x=10, y=12)

        glow_outer = tk.Frame(frame, bg="#111722", highlightbackground="#2EA043", highlightthickness=1)
        glow_outer.place(relx=0.5, rely=0.5, anchor="center", width=760, height=190)

        glow_inner = tk.Frame(glow_outer, bg="#0B1118", highlightbackground="#3DDC84", highlightthickness=1)
        glow_inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.97, relheight=0.9)

        center = tk.Frame(glow_inner, bg="#080C10")
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            center,
            text="Launching RANDOM AHH GAME by DOOMDADA",
            font=("Consolas", 13, "bold"),
            fg="#8AE234",
            bg="#080C10",
        ).pack(anchor="center", pady=(0, 12))

        progress = ttk.Progressbar(center, mode="determinate", length=700, maximum=100)
        progress.pack(pady=(0, 10), anchor="center")

        status = tk.StringVar(value="Initializing virtual environment...")
        tk.Label(center, textvariable=status, font=("Consolas", 11), fg="#FFFFFF", bg="#080C10").pack(
            anchor="center"
        )

        phases = [
            (15, "Loading challenge modules..."),
            (35, "Mounting bridge storyline..."),
            (60, "Activating terminal overlays..."),
            (85, "Preparing score systems..."),
            (100, "Boot complete."),
        ]

        def tick() -> None:
            value = int(progress["value"]) + 2
            progress["value"] = min(value, 100)
            for threshold, text in phases:
                if progress["value"] <= threshold:
                    status.set(text)
                    break
            if progress["value"] >= 100:
                self._build_main_layout()
                return
            self.root.after(30, tick)

        tick()

    def _show_startup_login_gate(self) -> bool:
        gate = tk.Toplevel(self.root)
        gate.title("VM Login")
        gate.geometry("520x300")
        gate.configure(bg="#080C10")
        gate.grab_set()
        gate.attributes("-topmost", True)
        gate.protocol("WM_DELETE_WINDOW", lambda: gate.destroy())

        result = {"ok": False}
        attempts = {"left": 3}

        frame = tk.Frame(gate, bg="#080C10", highlightbackground="#D70A53", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(
            frame,
            text="[ VIRTUAL BOX LOGIN ]",
            font=("Consolas", 16, "bold"),
            fg="#FF4477",
            bg="#080C10",
        ).pack(anchor="w", padx=12, pady=(12, 8))

        tk.Label(
            frame,
            text="Authenticate to launch RANDOM AHH GAME",
            font=("Consolas", 10),
            fg="#8AE234",
            bg="#080C10",
        ).pack(anchor="w", padx=12, pady=(0, 10))

        row1 = tk.Frame(frame, bg="#080C10")
        row1.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(row1, text="Username:", font=("Consolas", 11), fg="#FFFFFF", bg="#080C10").pack(side="left")
        user_var = tk.StringVar()
        user_entry = tk.Entry(
            row1,
            textvariable=user_var,
            width=24,
            font=("Consolas", 11),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
        )
        user_entry.pack(side="left", padx=(10, 0))

        row2 = tk.Frame(frame, bg="#080C10")
        row2.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(row2, text="Password:", font=("Consolas", 11), fg="#FFFFFF", bg="#080C10").pack(side="left")
        pass_var = tk.StringVar()
        pass_entry = tk.Entry(
            row2,
            textvariable=pass_var,
            width=24,
            font=("Consolas", 11),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
            show="*",
        )
        pass_entry.pack(side="left", padx=(10, 0))

        status_var = tk.StringVar(value="Attempts left: 3")
        tk.Label(frame, textvariable=status_var, font=("Consolas", 10), fg="#FFD166", bg="#080C10").pack(
            anchor="w", padx=12, pady=(0, 10)
        )

        def try_login() -> None:
            if user_var.get().strip().upper() == "DOOM" and pass_var.get().strip().upper() == "DADA":
                result["ok"] = True
                gate.destroy()
                return

            attempts["left"] -= 1
            if attempts["left"] <= 0:
                messagebox.showerror("ACCESS DENIED", "Too many failed attempts.")
                gate.destroy()
                return

            status_var.set(f"Attempts left: {attempts['left']}")
            messagebox.showwarning("ACCESS DENIED", "Wrong username or password.")

        actions = tk.Frame(frame, bg="#080C10")
        actions.pack(anchor="w", padx=12)
        tk.Button(
            actions,
            text="LOGIN",
            command=try_login,
            font=("Consolas", 10, "bold"),
            fg="#FFFFFF",
            bg="#D70A53",
            activebackground="#B70844",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            actions,
            text="EXIT",
            command=gate.destroy,
            font=("Consolas", 10, "bold"),
            fg="#FFFFFF",
            bg="#374151",
            activebackground="#1F2937",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(side="left")

        user_entry.focus_set()
        pass_entry.bind("<Return>", lambda _event: try_login())
        gate.update_idletasks()
        gate.deiconify()
        gate.lift()
        gate.focus_force()
        gate.wait_window()
        return bool(result["ok"])

    def _show_loading_transition(self) -> None:
        loader = tk.Toplevel(self.root)
        loader.title("Booting...")
        loader.geometry("520x170")
        loader.configure(bg="#080C10")
        loader.grab_set()
        loader.attributes("-topmost", True)

        frame = tk.Frame(loader, bg="#080C10", highlightbackground="#D70A53", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            frame,
            text="Launching RANDOM AHH GAME by DOOMDADA",
            font=("Consolas", 11, "bold"),
            fg="#8AE234",
            bg="#080C10",
        ).pack(anchor="w", padx=12, pady=(14, 10))

        progress = ttk.Progressbar(frame, mode="determinate", length=470, maximum=100)
        progress.pack(padx=12, pady=(0, 8))
        status = tk.StringVar(value="Initializing virtual environment...")
        tk.Label(frame, textvariable=status, font=("Consolas", 10), fg="#FFFFFF", bg="#080C10").pack(
            anchor="w", padx=12
        )

        phases = [
            (15, "Loading challenge modules..."),
            (35, "Mounting bridge storyline..."),
            (60, "Activating terminal overlays..."),
            (85, "Preparing score systems..."),
            (100, "Boot complete."),
        ]

        def tick() -> None:
            value = int(progress["value"]) + 2
            progress["value"] = min(value, 100)
            for threshold, text in phases:
                if progress["value"] <= threshold:
                    status.set(text)
                    break
            if progress["value"] >= 100:
                loader.destroy()
                return
            loader.after(35, tick)

        loader.update_idletasks()
        loader.deiconify()
        loader.lift()
        loader.focus_force()
        tick()
        loader.wait_window()

    def _setup_style(self) -> None:
        mono = "Consolas"
        self.style.configure(".", background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TLabelframe", background=self.colors["panel"], bordercolor=self.colors["accent"])
        self.style.configure("TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["accent"])
        self.style.configure("Title.TLabel", font=(mono, 20, "bold"), foreground=self.colors["accent"], background=self.colors["bg"])
        self.style.configure("SubTitle.TLabel", font=(mono, 12, "bold"), foreground=self.colors["terminal"], background=self.colors["bg"])
        self.style.configure("Body.TLabel", font=(mono, 11), foreground=self.colors["text"], background=self.colors["panel"])
        self.style.configure("Game.TButton", font=(mono, 10, "bold"), padding=8, background=self.colors["accent"], foreground="#FFFFFF")
        self.style.map("Game.TButton", background=[("active", "#B70844")], foreground=[("active", "#FFFFFF")])
        self.style.configure("TCheckbutton", background=self.colors["bg"], foreground=self.colors["text"], font=(mono, 10))
        self.style.map("TCheckbutton", foreground=[("active", self.colors["terminal"])])
        self.style.configure(
            "Game.TEntry",
            fieldbackground="#0A0F14",
            foreground="#FFFFFF",
            insertcolor="#8AE234",
            bordercolor="#D70A53",
            lightcolor="#D70A53",
            darkcolor="#D70A53",
            padding=6,
        )

    def _build_main_layout(self) -> None:
        self._clear_root()
        self.root.title("Reverse Engineering Game - Webinar Edition")

        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer,
            bg=self.colors["bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        wrapper = tk.Frame(canvas, bg="#080C10")
        window_id = canvas.create_window((0, 0), window=wrapper, anchor="nw")

        # Reuse the same full-screen animated background feel from login/loading.
        self._start_startup_hacker_background(wrapper, "main")
        haze = tk.Frame(wrapper, bg="#070A0E")
        haze.place(relx=0, rely=0, relwidth=1, relheight=1)
        haze.lower()

        # Use pack-based foreground layout so geometry stays stable inside the scroll canvas.
        shadow = tk.Frame(wrapper, bg="#020304")
        shadow.pack(fill="both", expand=True, padx=(40, 24), pady=(34, 18))

        glow_outer = tk.Frame(wrapper, bg="#111722", highlightbackground="#2EA043", highlightthickness=1)
        glow_outer.pack(fill="both", expand=True, padx=(28, 36), pady=(22, 30))

        glow_inner = tk.Frame(glow_outer, bg="#0B1118", highlightbackground="#3DDC84", highlightthickness=1)
        glow_inner.pack(fill="both", expand=True, padx=6, pady=6)

        content = ttk.Frame(glow_inner, padding=16)
        content.pack(fill="both", expand=True)

        def on_wrapper_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def on_mousewheel(event: tk.Event) -> None:
            if hasattr(event, "delta") and event.delta:
                canvas.yview_scroll(int(-event.delta / 120), "units")

        wrapper.bind("<Configure>", on_wrapper_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        header = ttk.Frame(content)
        header.pack(fill="x")

        doomdada_banner = (
            "  ____   ___   ___  __  __ ____    _    ____    _    \n"
            " |  _ \\ / _ \\ / _ \\|  \\/  |  _ \\  / \\  |  _ \\  / \\   \n"
            " | | | | | | | | | | |\\/| | | | |/ _ \\ | | | |/ _ \\  \n"
            " | |_| | |_| | |_| | |  | | |_| / ___ \\| |_| / ___ \\ \n"
            " |____/ \\___/ \\___/|_|  |_|____/_/   \\_\\____/_/   \\_\\\n"
            "                     M I N I G A M E                    "
        )
        ttk.Label(header, text=doomdada_banner, style="SubTitle.TLabel", justify="center").pack(anchor="center")

        ttk.Label(header, text="Reverse Engineering Game", style="Title.TLabel").pack(anchor="center")
        ttk.Label(
            header,
            text="RANDOM AHH GAME by DOOMDADA",
            style="SubTitle.TLabel",
        ).pack(anchor="center", pady=(4, 12))
        self.prompt_base = "root@doomdada:~$ ./reverse_engineering_game_gui.py"
        self.cursor_visible = True
        self.prompt_var = tk.StringVar(value=self.prompt_base + " _")
        ttk.Label(header, textvariable=self.prompt_var, style="Body.TLabel").pack(anchor="center", pady=(0, 12))
        self._blink_cursor()

        info_frame = ttk.LabelFrame(content, text="Mission Brief", padding=12)
        info_frame.pack(fill="x")

        info_text = (
            "Reverse engineering means figuring out how a program works, even if\n"
            "you do not have its original code. In security, it helps us inspect\n"
            "how apps behave and spot possible weaknesses."
        )
        ttk.Label(info_frame, text=info_text, style="Body.TLabel", justify="left").pack(anchor="w")

        controls = ttk.Frame(content)
        controls.pack(fill="x", pady=14)

        self.player_name_var = tk.StringVar(value="Presenter")
        self.timed_mode_var = tk.BooleanVar(value=False)
        self.classroom_mode_var = tk.BooleanVar(value=True)

        row_top = ttk.Frame(controls)
        row_top.pack(fill="x", pady=(0, 6))
        row_mid = ttk.Frame(controls)
        row_mid.pack(fill="x", pady=(0, 6))
        row_bottom = ttk.Frame(controls)
        row_bottom.pack(fill="x")

        ttk.Label(row_top, text="Player:", style="Body.TLabel").pack(side="left", padx=(0, 6))
        ttk.Entry(row_top, textvariable=self.player_name_var, width=16).pack(side="left", padx=(0, 10))
        ttk.Button(row_top, text="What is Rev.Eng?", style="Game.TButton", command=self.show_about).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row_top, text="How to Play", style="Game.TButton", command=self.show_how_to_play).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row_top, text="Beginner Tutorial", style="Game.TButton", command=self.show_tutorial).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row_top, text="Story Intro", style="Game.TButton", command=self.show_story_intro).pack(
            side="left", padx=(0, 8)
        )

        ttk.Checkbutton(
            row_mid,
            text="Boost Mode",
            variable=self.boost_mode_var,
            command=self._on_boost_mode_changed,
        ).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(row_mid, text="Runner Hint Mode", variable=self.hint_mode_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(row_mid, text="Mute SFX", variable=self.mute_sfx_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(row_mid, text="Timed Mode (60s)", variable=self.timed_mode_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(row_mid, text="Classroom Mode", variable=self.classroom_mode_var).pack(side="left")

        ttk.Button(row_bottom, text="Leaderboard", style="Game.TButton", command=self.show_leaderboard).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row_bottom, text="Team Scores", style="Game.TButton", command=self.show_team_scores).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row_bottom, text="Submit Score", style="Game.TButton", command=self.submit_score).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(row_bottom, text="Reset Score", style="Game.TButton", command=self.reset_progress).pack(
            side="left"
        )

        game_panel = ttk.LabelFrame(content, text="Choose Difficulty", padding=12)
        game_panel.pack(fill="both", expand=True)

        game_body = ttk.Frame(game_panel)
        game_body.pack(fill="both", expand=True)

        grid = ttk.Frame(game_body)
        grid.pack(side="left", fill="both", expand=True)

        right_panel = ttk.LabelFrame(game_body, text="Live Code Runner", padding=8)
        right_panel.pack(side="left", fill="both", padx=(10, 0))
        self._build_live_code_runner(right_panel)

        self._make_level_button(grid, "Easy", 0, 0)
        self._make_level_button(grid, "Medium", 0, 1)
        self._make_level_button(grid, "Hard", 1, 0)
        self._make_level_button(grid, "XHARD", 1, 1)
        self._make_level_button(grid, "CRAZY", 2, 0)
        self._make_level_button(grid, "DOOMDADA", 2, 1)

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        grid.rowconfigure(2, weight=1)

        status_box = ttk.LabelFrame(content, text="Live Status", padding=12)
        status_box.pack(fill="x", pady=(14, 0))

        self.score_var = tk.StringVar(value="Score: 0")
        self.completed_var = tk.StringVar(value="Completed: None")

        ttk.Label(status_box, textvariable=self.score_var, style="SubTitle.TLabel").pack(anchor="w")
        ttk.Label(status_box, textvariable=self.completed_var, style="Body.TLabel").pack(anchor="w", pady=(6, 0))

    def _make_level_button(self, parent: ttk.Frame, level: str, row: int, col: int) -> None:
        data = self.levels[level]
        if level == "DOOMDADA":
            card = tk.Frame(
                parent,
                bg="#1C2128",
                highlightbackground="#D70A53",
                highlightcolor="#D70A53",
                highlightthickness=2,
                bd=0,
            )
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            self.doomdada_card_widget = card
            if self.doomdada_pulse_job is None:
                self._pulse_doomdada_card()

            tk.Label(card, text=f"{level}", font=("Consolas", 12, "bold"), fg="#8AE234", bg="#1C2128").pack(
                anchor="w", padx=12, pady=(12, 0)
            )
            tk.Label(card, text=data["desc"], font=("Consolas", 11), fg="#FFFFFF", bg="#1C2128").pack(
                anchor="w", padx=12, pady=(4, 10)
            )
            tk.Label(card, text=f"Points: {data['points']}", font=("Consolas", 11), fg="#FFFFFF", bg="#1C2128").pack(
                anchor="w", padx=12, pady=(0, 10)
            )
            ttk.Button(
                card,
                text=f"Play {level}",
                style="Game.TButton",
                command=lambda lv=level: self.open_challenge(lv),
            ).pack(anchor="w", padx=12, pady=(0, 12))
            return

        card = ttk.Frame(parent, padding=12, relief="solid")
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

        ttk.Label(card, text=f"{level}", style="SubTitle.TLabel").pack(anchor="w")
        ttk.Label(card, text=data["desc"], style="Body.TLabel").pack(anchor="w", pady=(4, 10))
        ttk.Label(card, text=f"Points: {data['points']}", style="Body.TLabel").pack(anchor="w", pady=(0, 10))

        ttk.Button(
            card,
            text=f"Play {level}",
            style="Game.TButton",
            command=lambda lv=level: self.open_challenge(lv),
        ).pack(anchor="w")

    def _build_live_code_runner(self, parent: ttk.LabelFrame) -> None:
        ttk.Label(
            parent,
            text="Functional animation: simulated runner + controls",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(0, 6))

        self.main_code_box = tk.Text(
            parent,
            wrap="none",
            width=42,
            height=26,
            font=("Consolas", 9),
            bg="#0A0F14",
            fg="#8AE234",
            insertbackground="#8AE234",
            relief="flat",
        )
        self.main_code_box.pack(fill="both", expand=True)

        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=self.main_code_box.xview)
        self.main_code_box.configure(xscrollcommand=xscroll.set)
        xscroll.pack(fill="x", pady=(4, 0))

        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(8, 0))

        ttk.Button(controls, text="Pause", style="Game.TButton", command=self._pause_main_code_runner).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(controls, text="Resume", style="Game.TButton", command=self._resume_main_code_runner).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(controls, text="Inject Task", style="Game.TButton", command=self._inject_main_code_task).pack(
            side="left"
        )

        self._append_main_code_line("[boot] main-screen code runner online")
        self._resume_main_code_runner()

    def _append_main_code_line(self, text: str) -> None:
        if self.main_code_box is None or not self.main_code_box.winfo_exists():
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.main_code_box.insert("end", f"[{timestamp}] {text}\n")
        line_count = int(float(self.main_code_box.index("end-1c").split(".")[0]))
        if line_count > 180:
            self.main_code_box.delete("1.0", "30.0")
        self.main_code_box.see("end")

    def _next_code_line(self) -> str:
        if self.hint_mode_var.get():
            focus_level = self.active_level
            if not focus_level:
                for level_name in self.levels:
                    if level_name not in self.completed_levels:
                        focus_level = level_name
                        break
            hint_lines = {
                "Easy": [
                    "hint.easy -> unscramble the bridge word first",
                    "hint.easy -> wrap final as DOOM{WORD}",
                ],
                "Medium": [
                    "hint.medium -> EARLYBIRD uses E->3 and I->1",
                    "hint.medium -> keep inner quotes in this level",
                ],
                "Hard": [
                    "hint.hard -> apply uppercase at exact positions only",
                    "hint.hard -> case mistakes fail the checker",
                ],
                "XHARD": [
                    "hint.xhard -> collect all real fragments before submit",
                    "hint.xhard -> reset happens after too many decoys",
                ],
                "CRAZY": [
                    "hint.crazy -> breathe, click near 6.7 seconds",
                    "hint.crazy -> success window is tight but fair",
                ],
                "DOOMDADA": [
                    "hint.doomdada -> trace seed -> leet -> case pattern",
                    "hint.doomdada -> symbol placement matters",
                ],
            }
            if focus_level in hint_lines:
                return random.choice(hint_lines[focus_level])

        options = [
            "scan_level('Easy') -> sig='PMTOOCBA'",
            "decode.medium(tag='EARLYBIRD') -> 3ARLYB1RD",
            "mask.apply('ambatukammm', idx=[1,3,6]) -> AmBatUkammm",
            "xhard.blocks.read(slot=7) -> clue='_7HE'",
            "crazy.timer.sync(target=6.7, tol=0.12)",
            "doomdada.gate.auth(user='DOOM', status='granted')",
            "leaderboard.update(player='Presenter', mode='Classroom')",
            "team.score.bump(team='Blue', points=50)",
            "console.exec(sandbox=True) -> result='safe'",
            "trace.combine(parts=['WE','_7HE','_B3ST'])",
        ]
        return random.choice(options)

    def _tick_main_code_runner(self) -> None:
        if not self.main_code_running:
            self.main_code_job = None
            return
        if self.main_code_box is None or not self.main_code_box.winfo_exists():
            self.main_code_job = None
            self.main_code_running = False
            return
        self._append_main_code_line(self._next_code_line())
        self.main_code_job = self.root.after(random.randint(280, 640), self._tick_main_code_runner)

    def _pause_main_code_runner(self) -> None:
        self.main_code_running = False
        if self.main_code_job:
            try:
                self.root.after_cancel(self.main_code_job)
            except Exception:
                pass
            self.main_code_job = None
        self._append_main_code_line("[runner] paused")

    def _resume_main_code_runner(self) -> None:
        if self.main_code_running:
            return
        self.main_code_running = True
        self._append_main_code_line("[runner] resumed")
        self._tick_main_code_runner()

    def _inject_main_code_task(self) -> None:
        burst = [
            "task.inject('analyze_xhard_board')",
            "collect(['BL0CK','_','HUNT','_FLAG'])",
            "format.flag('DOOM{BL0CK_HUNT_FLAG}')",
        ]
        for line in burst:
            self._append_main_code_line(line)

    def _blink_cursor(self) -> None:
        suffix = " _" if self.cursor_visible else "  "
        self.prompt_var.set(self.prompt_base + suffix)
        self.cursor_visible = not self.cursor_visible
        self.root.after(550, self._blink_cursor)

    def _show_terminal_popup(self, title: str, message: str, width: int = 760, height: int = 500) -> None:
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry(f"{width}x{height}")
        popup.configure(bg="#080C10")
        popup.transient(self.root)
        popup.grab_set()

        frame = tk.Frame(popup, bg="#080C10", highlightbackground="#D70A53", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            frame,
            text=f"[ {title.upper()} ]",
            font=("Consolas", 14, "bold"),
            fg="#8AE234",
            bg="#080C10",
        ).pack(anchor="w", padx=10, pady=(10, 8))

        body_wrap = tk.Frame(frame, bg="#080C10")
        body_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scrollbar = ttk.Scrollbar(body_wrap, orient="vertical")
        body = tk.Text(
            body_wrap,
            wrap="word",
            font=("Consolas", 10),
            bg="#0A0F14",
            fg="#C9D1D9",
            insertbackground="#8AE234",
            relief="flat",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=body.yview)
        body.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        body.insert("1.0", message)
        body.config(state="disabled")

        tk.Button(
            frame,
            text="CLOSE",
            command=popup.destroy,
            font=("Consolas", 10, "bold"),
            fg="#FFFFFF",
            bg="#D70A53",
            activebackground="#B70844",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(anchor="e", padx=10, pady=(0, 10))

        popup.wait_window()

    def show_about(self) -> None:
        message = (
            "What is Reverse Engineering?\n\n"
            "Reverse engineering means taking something already built and studying\n"
            "it to understand how it works.\n\n"
            "What it does:\n"
            "- Reveals hidden logic\n"
            "- Shows how checks and rules are applied\n"
            "- Helps investigate suspicious software\n\n"
            "Purpose:\n"
            "- Security auditing and defense\n"
            "- Software trust verification\n"
            "- Cybersecurity training and CTF practice\n\n"
            "Always practice legally and ethically."
        )
        self._show_terminal_popup("What is Reverse Engineering?", message)

    def show_how_to_play(self) -> None:
        message = (
            "How to Play\n\n"
            "1) Pick a difficulty level.\n"
            "2) Read the puzzle instructions carefully.\n"
            "3) Submit your answer in flag format: DOOM{...}.\n"
            "4) Standard levels use 3 attempts per challenge.\n"
            "5) Correct answer gives points and marks level complete.\n"
            "6) Optional timed mode gives 60 seconds per challenge.\n\n"
            "Scoring\n"
            "- Easy: 50\n"
            "- Medium: 100\n"
            "- Hard: 150\n"
            "- XHARD: 200\n"
            "- CRAZY: 250\n"
            "- DOOMDADA: 300"
        )
        self._show_terminal_popup("How to Play", message)

    def show_tutorial(self) -> None:
        message = (
            "Beginner Tutorial (No Python Needed)\n\n"
            "How to read a challenge:\n"
            "1) Follow lines top to bottom like calculator steps.\n"
            "2) Track the variable after each line.\n"
            "3) For loops, repeat the same step several times.\n\n"
            "Symbol quick guide:\n"
            "- = means assign value\n"
            "- + means add\n"
            "- ^ means compare binary bits and mix values\n"
            "- % means remainder\n"
            "- ord(letter) means convert letter to a number\n\n"
            "You do not need to write code to solve this game.\n"
            "Use the hints and solve it like a logic puzzle."
        )
        self._show_terminal_popup("Beginner Tutorial", message)

    def show_story_intro(self) -> None:
        message = (
            "Story Intro\n\n"
            "Chapter 1 - Bridge Note:\n"
            "You find a scrambled clue under the bridge.\n\n"
            "Chapter 2 - Earl's Tag:\n"
            "A stage-name signature appears as EARLYBIRD.\n\n"
            "Chapter 3 - Mask Pattern:\n"
            "A log file reveals strict letter-case control.\n\n"
            "Chapter 4 - XHARD Block Hunt:\n"
            "You search memory blocks to uncover true clue fragments.\n\n"
            "Chapter 5 - CRAZY Reaction Core:\n"
            "You must stop the timer at exactly 6.7 seconds.\n\n"
            "Chapter 6 - DOOMDADA Lockdown:\n"
            "Terminal lock, password gate, and final scripted decode.\n\n"
            "Goal: Trace each step and reconstruct the final flag with precision."
        )
        self._show_terminal_popup("Story Intro", message)

    def reset_progress(self) -> None:
        if messagebox.askyesno("Reset Progress", "Reset score and completed levels?"):
            self._reset_progress_silent()

    def _reset_progress_silent(self) -> None:
        self.total_score = 0
        self.completed_levels.clear()
        self.doomdada_attempts_left = 3
        self.end_credits_shown = False
        self.team_scores = {}
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.score_var.set(f"Score: {self.total_score}")
        if self.completed_levels:
            completed = ", ".join(sorted(self.completed_levels))
        else:
            completed = "None"
        self.completed_var.set(f"Completed: {completed}")

    def _load_leaderboard(self) -> list[dict[str, str | int]]:
        if not self.leaderboard_path.exists():
            return []
        try:
            return json.loads(self.leaderboard_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_leaderboard(self) -> None:
        self.leaderboard_path.write_text(json.dumps(self.leaderboard_data, indent=2), encoding="utf-8")

    def submit_score(self) -> None:
        player = self.player_name_var.get().strip() or "Player"
        record = {
            "player": player,
            "score": self.total_score,
            "completed": len(self.completed_levels),
            "timed_mode": "ON" if self.timed_mode_var.get() else "OFF",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.leaderboard_data.append(record)
        self.leaderboard_data.sort(key=lambda x: int(x["score"]), reverse=True)
        self.leaderboard_data = self.leaderboard_data[:15]
        self._save_leaderboard()
        self._show_terminal_popup("Score Submitted", f"Saved score {self.total_score} for {player}.", width=540, height=240)

    def show_leaderboard(self) -> None:
        if not self.leaderboard_data:
            self._show_terminal_popup("Leaderboard", "No scores saved yet. Use Submit Score first.", width=640, height=260)
            return

        lines = ["Top Scores"]
        for idx, item in enumerate(self.leaderboard_data[:10], start=1):
            line = (
                f"{idx:>2}. {item['player']} | Score: {item['score']} | "
                f"Levels: {item['completed']}/4 | Timed: {item['timed_mode']}"
            )
            lines.append(line)
        self._show_terminal_popup("Leaderboard", "\n".join(lines), width=760, height=420)

    def show_team_scores(self) -> None:
        if not self.team_scores:
            self._show_terminal_popup("Team Scores", "No team scores yet. Solve levels to populate this board.", width=660, height=260)
            return

        ranked = sorted(self.team_scores.items(), key=lambda kv: kv[1], reverse=True)
        lines = ["Live Team Scores"]
        for idx, (team, score) in enumerate(ranked, start=1):
            lines.append(f"{idx:>2}. {team} - {score}")
        self._show_terminal_popup("Team Scores", "\n".join(lines), width=700, height=400)

    def _award_team_points(self, points: int) -> None:
        team = self.player_name_var.get().strip() or "Team"
        self.team_scores[team] = self.team_scores.get(team, 0) + points

    def _show_level_debrief(self, level_name: str, level_data: dict[str, object]) -> None:
        mistakes = level_data.get("common_mistakes", [])
        if isinstance(mistakes, list):
            mistake_lines = "\n".join(f"- {m}" for m in mistakes[:3])
        else:
            mistake_lines = "- Focus on exact formatting"

        debrief = (
            f"Debrief - {level_name}\n\n"
            f"What was the trick?\n{level_data.get('learning_goal', 'Apply the rule step-by-step.')}\n\n"
            f"Where people usually fail:\n{mistake_lines}\n\n"
            f"Real-world relevance:\n{level_data.get('real_world', 'This builds analysis accuracy.')}"
        )
        self._show_terminal_popup(f"Debrief - {level_name}", debrief, width=760, height=460)

    def _stop_timer(self) -> None:
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def _tick_timer(self) -> None:
        if not self.challenge_window or not self.challenge_window.winfo_exists():
            self._stop_timer()
            return

        self.time_left -= 1
        self._refresh_attempt_label()

        if self.time_left <= 0:
            self.feedback_var.set("Time is up. Challenge locked.")
            data = self.levels[self.active_level]
            messagebox.showwarning("Time Up", f"Time expired. Answer: {data['expected']}")
            self._stop_timer()
            return

        self.timer_job = self.root.after(1000, self._tick_timer)

    def _refresh_attempt_label(self) -> None:
        if not hasattr(self, "attempt_var"):
            return
        if self.timed_mode_var.get() and self.time_left > 0:
            self.attempt_var.set(f"Attempts left: {self.attempts_left} | Time left: {self.time_left}s")
            return
        self.attempt_var.set(f"Attempts left: {self.attempts_left}")

    def _on_challenge_close(self) -> None:
        self._stop_timer()
        self._stop_doomdada_scanline()
        if self.challenge_window and self.challenge_window.winfo_exists():
            self.challenge_window.destroy()

    def _on_boost_mode_changed(self) -> None:
        self._apply_boost_mode_ui()
        if self.side_info_box is None:
            return
        if self.boost_mode_var.get():
            self._set_side_panel("Boost Mode enabled: Cheatsheet, function guide, and starter snippets are active.")
        else:
            self._set_side_panel("Boost Mode disabled: Solve with minimal guidance for stronger challenge.")

    def _apply_boost_mode_ui(self) -> None:
        state = "normal" if self.boost_mode_var.get() else "disabled"
        for widget in self.boost_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def open_challenge(self, level: str) -> None:
        if level == "XHARD":
            self._open_xhard_puzzle()
            return

        if level == "CRAZY":
            self._open_crazy_reaction_game()
            return

        if level == "DOOMDADA":
            granted = self._show_doomdada_access_gate()
            if not granted:
                return

        if self.challenge_window is not None and self.challenge_window.winfo_exists():
            self._stop_doomdada_scanline()
            self.challenge_window.destroy()
            self._stop_timer()

        self.active_level = level
        self.level_start_time[level] = time.perf_counter()
        self.level_submit_counts[level] = 0
        self.attempts_left = self.doomdada_attempts_left if level == "DOOMDADA" else 3
        self.boost_widgets = []
        data = self.levels[level]

        self.challenge_window = tk.Toplevel(self.root)
        self.challenge_window.title(f"Challenge - {level}")
        self.challenge_window.geometry("820x560")
        self.challenge_window.configure(bg=self.colors["bg"])
        self.challenge_window.protocol("WM_DELETE_WINDOW", self._on_challenge_close)

        frame = ttk.Frame(self.challenge_window, padding=14)
        frame.pack(fill="both", expand=True)

        if level == "DOOMDADA":
            self.doomdada_alert_bar = tk.Label(
                frame,
                text="[ DOOMDADA MONITOR ] Threat level: NORMAL",
                font=("Consolas", 10, "bold"),
                fg="#A7F3D0",
                bg="#102016",
                padx=8,
                pady=6,
            )
            self.doomdada_alert_bar.pack(fill="x", pady=(0, 8))
            self._start_doomdada_scanline(frame)
        else:
            self.doomdada_alert_bar = None
            self._stop_doomdada_scanline()

        ttk.Label(frame, text=f"{level} Challenge", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text=data["desc"], style="SubTitle.TLabel").pack(anchor="w", pady=(4, 10))

        split = ttk.Frame(frame)
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=3)
        split.columnconfigure(1, weight=2)

        left_col = ttk.Frame(split)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_col = ttk.LabelFrame(split, text="Guidance Panel", padding=8)
        right_col.grid(row=0, column=1, sticky="nsew")

        code_box = tk.Text(
            left_col,
            wrap="word",
            height=14,
            font=("Consolas", 11),
            bg=self.colors["code_bg"],
            fg=self.colors["code_text"],
            insertbackground=self.colors["terminal"],
            relief="flat",
        )
        code_box.insert("1.0", data["content"])
        code_box.config(state="disabled")
        code_box.pack(fill="both", expand=False)

        ttk.Label(left_col, text=data["hint"], style="Body.TLabel").pack(anchor="w", pady=(10, 8))

        ttk.Label(left_col, text=f"Learning Goal: {data.get('learning_goal', 'Apply puzzle rules carefully.')}", style="Body.TLabel").pack(
            anchor="w", pady=(0, 4)
        )

        input_row = ttk.Frame(left_col)
        input_row.pack(fill="x")
        ttk.Label(input_row, text="Enter Flag:", style="Body.TLabel").pack(side="left")

        self.answer_var = tk.StringVar()
        self.attempt_var = tk.StringVar(value=f"Attempts left: {self.attempts_left}")
        self.hint_index = 0
        entry = tk.Entry(
            input_row,
            textvariable=self.answer_var,
            width=36,
            font=("Consolas", 11),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            selectbackground="#D70A53",
            selectforeground="#FFFFFF",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
        )
        entry.pack(side="left", padx=10)
        entry.focus_set()
        entry.bind("<Return>", lambda _event: self.submit_answer())

        ttk.Button(input_row, text="Submit", style="Game.TButton", command=self.submit_answer).pack(side="left")

        ttk.Label(left_col, textvariable=self.attempt_var, style="Body.TLabel").pack(anchor="w", pady=(8, 0))

        self.feedback_var = tk.StringVar(value="Answer format required: DOOM{...}")
        ttk.Label(left_col, textvariable=self.feedback_var, style="Body.TLabel").pack(anchor="w", pady=(6, 0))

        guidance_buttons = ttk.Frame(left_col)
        guidance_buttons.pack(fill="x", pady=(8, 0))
        guidance_buttons.columnconfigure(0, weight=1)
        guidance_buttons.columnconfigure(1, weight=1)
        guidance_buttons.columnconfigure(2, weight=1)

        ttk.Button(
            guidance_buttons,
            text="Need Help?",
            style="Game.TButton",
            command=self.show_next_hint,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 6))
        ttk.Button(
            guidance_buttons,
            text="Walkthrough",
            style="Game.TButton",
            command=self.show_walkthrough,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(0, 6))
        ttk.Button(
            guidance_buttons,
            text="Why It Matters",
            style="Game.TButton",
            command=self.show_real_world,
        ).grid(row=0, column=2, sticky="ew", pady=(0, 6))
        ttk.Button(
            guidance_buttons,
            text="Common Mistakes",
            style="Game.TButton",
            command=self.show_common_mistakes,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 6))
        ttk.Button(
            guidance_buttons,
            text="Presenter Script",
            style="Game.TButton",
            command=self.show_presenter_script,
        ).grid(row=1, column=2, sticky="ew")
        ttk.Button(
            guidance_buttons,
            text="Trace Table",
            style="Game.TButton",
            command=self.show_trace_table,
        ).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        cheatsheet_btn = ttk.Button(
            guidance_buttons,
            text="Python Cheatsheet",
            style="Game.TButton",
            command=self.show_python_cheatsheet,
        )
        cheatsheet_btn.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 6), pady=(6, 0))
        purpose_btn = ttk.Button(
            guidance_buttons,
            text="Function Purpose",
            style="Game.TButton",
            command=self.show_function_purpose,
        )
        purpose_btn.grid(row=3, column=2, sticky="ew", pady=(6, 0))
        self.boost_widgets.extend([cheatsheet_btn, purpose_btn])

        self.side_info_box = tk.Text(
            right_col,
            wrap="word",
            width=36,
            height=16,
            font=("Consolas", 10),
            bg=self.colors["code_bg"],
            fg=self.colors["code_text"],
            relief="flat",
        )
        self.side_info_box.pack(fill="both", expand=True)
        self._set_side_panel(
            "Welcome to the guidance panel.\n\n"
            "Click any helper button to show explanations here while the challenge remains visible."
        )

        console_frame = ttk.LabelFrame(right_col, text="Mini Console", padding=6)
        console_frame.pack(fill="x", pady=(8, 0))

        self.console_input = tk.Text(
            console_frame,
            wrap="word",
            height=6,
            font=("Consolas", 10),
            bg="#0A0F14",
            fg="#FFFFFF",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
        )
        self.console_input.pack(fill="x")
        self.console_input.insert(
            "1.0",
            "# Try Python here. Examples:\n"
            "# build_flag()\n"
            "# result = build_flag(); print(result)\n",
        )

        console_controls = ttk.Frame(console_frame)
        console_controls.pack(fill="x", pady=(6, 0))
        ttk.Button(console_controls, text="Run Code", style="Game.TButton", command=self.run_console_code).pack(
            side="left"
        )
        ttk.Button(console_controls, text="Clear", style="Game.TButton", command=self.clear_console).pack(
            side="left", padx=(8, 0)
        )

        self.console_output_var = tk.StringVar(value="Console: waiting for input")
        ttk.Label(console_frame, textvariable=self.console_output_var, style="Body.TLabel").pack(anchor="w", pady=(6, 0))

        starter_frame = ttk.Frame(console_frame)
        starter_frame.pack(fill="x", pady=(8, 0))
        starter_frame.columnconfigure(0, weight=1)
        starter_frame.columnconfigure(1, weight=1)

        starter_1 = ttk.Button(
            starter_frame,
            text="Insert: Base Phrase",
            style="Game.TButton",
            command=lambda: self.insert_starter_snippet("base"),
        )
        starter_1.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 6))

        starter_2 = ttk.Button(
            starter_frame,
            text="Insert: Leet Stage",
            style="Game.TButton",
            command=lambda: self.insert_starter_snippet("leet"),
        )
        starter_2.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        starter_3 = ttk.Button(
            starter_frame,
            text="Insert: Case Stage",
            style="Game.TButton",
            command=lambda: self.insert_starter_snippet("case"),
        )
        starter_3.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        starter_4 = ttk.Button(
            starter_frame,
            text="Insert: Build Flag",
            style="Game.TButton",
            command=lambda: self.insert_starter_snippet("build"),
        )
        starter_4.grid(row=1, column=1, sticky="ew")

        self.boost_widgets.extend([starter_1, starter_2, starter_3, starter_4])
        self._apply_boost_mode_ui()

        self._refresh_attempt_label()

        if self.timed_mode_var.get():
            self.time_left = 60
            self._refresh_attempt_label()
            self.timer_job = self.root.after(1000, self._tick_timer)

    def _show_doomdada_access_gate(self) -> bool:
        gate = tk.Toplevel(self.root)
        gate.title("DOOMDADA ACCESS LOCK")
        gate.geometry("760x520")
        gate.configure(bg="#080C10")
        gate.transient(self.root)
        gate.grab_set()

        result = {"granted": False}
        animation = {"job": None, "running": True, "typed": 0, "bit_count": 0}

        frame = tk.Frame(gate, bg="#080C10", highlightbackground="#D70A53", highlightthickness=2)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        title = tk.Label(
            frame,
            text="[ DOOMDADA TERMINAL LOCKDOWN ]",
            font=("Consolas", 16, "bold"),
            fg="#FF4477",
            bg="#080C10",
        )
        title.pack(anchor="w", padx=12, pady=(12, 6))

        terminal = tk.Text(
            frame,
            wrap="word",
            height=15,
            font=("Consolas", 10),
            bg="#02070C",
            fg="#8AE234",
            insertbackground="#8AE234",
            relief="flat",
        )
        terminal.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        terminal_art = (
            "root@doomdada:~$ ./boot_lockdown.sh\n"
            "[!] WARNING: HIGH RISK ZONE - DOOMDADA ACCESS RESTRICTED\n"
            "[+] Initializing visual firewall...\n\n"
            "  ██████╗  ██████╗  ██████╗ ███╗   ███╗██████╗  █████╗ ██████╗  █████╗ \n"
            "  ██╔══██╗██╔═══██╗██╔═══██╗████╗ ████║██╔══██╗██╔══██╗██╔══██╗██╔══██╗\n"
            "  ██║  ██║██║   ██║██║   ██║██╔████╔██║██║  ██║███████║██║  ██║███████║\n"
            "  ██║  ██║██║   ██║██║   ██║██║╚██╔╝██║██║  ██║██╔══██║██║  ██║██╔══██║\n"
            "  ██████╔╝╚██████╔╝╚██████╔╝██║ ╚═╝ ██║██████╔╝██║  ██║██████╔╝██║  ██║\n"
            "  ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝\n\n"
            "LOCK: [##########] ACTIVE\n"
            "BINARY STREAM:"
        )

        def append_terminal(text: str) -> None:
            terminal.config(state="normal")
            terminal.insert("end", text)
            terminal.see("end")
            terminal.config(state="disabled")

        def animate_terminal() -> None:
            if not animation["running"] or not gate.winfo_exists():
                return

            if animation["typed"] < len(terminal_art):
                chunk = terminal_art[animation["typed"] : animation["typed"] + 4]
                animation["typed"] += len(chunk)
                append_terminal(chunk)
                animation["job"] = gate.after(25, animate_terminal)
                return

            # After intro text is fully typed, keep streaming binary bits like a live terminal feed.
            bit = str(random.randint(0, 1))
            append_terminal(bit)
            animation["bit_count"] += 1

            if animation["bit_count"] % 4 == 0:
                append_terminal(" ")
            if animation["bit_count"] % 64 == 0:
                append_terminal("\n")

            # Keep the output window scrolling and trimmed so the stream looks "moving".
            current_lines = int(float(terminal.index("end-1c").split(".")[0]))
            if current_lines > 24:
                terminal.config(state="normal")
                terminal.delete("1.0", "3.0")
                terminal.config(state="disabled")

            animation["job"] = gate.after(35, animate_terminal)

        def close_gate(granted: bool = False) -> None:
            result["granted"] = granted
            animation["running"] = False
            if animation["job"] is not None:
                try:
                    gate.after_cancel(animation["job"])
                except Exception:
                    pass
                animation["job"] = None
            if gate.winfo_exists():
                gate.destroy()

        gate.protocol("WM_DELETE_WINDOW", lambda: close_gate(False))

        hint_label = tk.Label(
            frame,
            text="Hint: DOOMDADA/HARVZ REQUs favorite fruit - green outside, and red inside, with black seeds",
            font=("Consolas", 10, "bold"),
            fg="#FFD166",
            bg="#080C10",
        )
        hint_label.pack(anchor="w", padx=12, pady=(0, 8))

        input_row = tk.Frame(frame, bg="#080C10")
        input_row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(input_row, text="Password:", font=("Consolas", 11), fg="#FFFFFF", bg="#080C10").pack(side="left")
        password_var = tk.StringVar()
        password_entry = tk.Entry(
            input_row,
            textvariable=password_var,
            width=28,
            font=("Consolas", 11),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
            show="*",
        )
        password_entry.pack(side="left", padx=10)
        password_entry.focus_set()

        def unlock() -> None:
            if password_var.get().strip().upper() == "WATERMELON":
                close_gate(True)
                return
            messagebox.showwarning("ACCESS DENIED", "Wrong password. Try again.")

        tk.Button(
            input_row,
            text="UNLOCK",
            command=unlock,
            font=("Consolas", 10, "bold"),
            fg="#FFFFFF",
            bg="#D70A53",
            activebackground="#B70844",
            relief="flat",
            padx=10,
            pady=6,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            input_row,
            text="ABORT",
            command=lambda: close_gate(False),
            font=("Consolas", 10, "bold"),
            fg="#FFFFFF",
            bg="#374151",
            activebackground="#1F2937",
            relief="flat",
            padx=10,
            pady=6,
        ).pack(side="left")

        password_entry.bind("<Return>", lambda _event: unlock())
        animate_terminal()

        gate.wait_window()
        return bool(result["granted"])

    def _open_xhard_puzzle(self) -> None:
        if self.challenge_window is not None and self.challenge_window.winfo_exists():
            self.challenge_window.destroy()
            self._stop_timer()

        self.active_level = "XHARD"
        self.level_start_time["XHARD"] = time.perf_counter()
        self.level_submit_counts["XHARD"] = 0
        self.attempts_left = 3
        data = self.levels["XHARD"]

        win = tk.Toplevel(self.root)
        win.title("Challenge - XHARD")
        win.geometry("900x620")
        win.configure(bg=self.colors["bg"])
        self.challenge_window = win
        win.protocol("WM_DELETE_WINDOW", self._on_challenge_close)

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="XHARD - BLOCK HUNT", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text=data["desc"], style="SubTitle.TLabel").pack(anchor="w", pady=(4, 10))

        story = tk.Text(
            frame,
            wrap="word",
            height=6,
            font=("Consolas", 10),
            bg=self.colors["code_bg"],
            fg=self.colors["code_text"],
            relief="flat",
        )
        story.insert("1.0", str(data["content"]))
        story.config(state="disabled")
        story.pack(fill="x")

        split = ttk.Frame(frame)
        split.pack(fill="both", expand=True, pady=(10, 0))
        split.columnconfigure(0, weight=2)
        split.columnconfigure(1, weight=1)

        board = ttk.LabelFrame(split, text="Memory Blocks", padding=10)
        board.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        side = ttk.LabelFrame(split, text="Collected Clues", padding=10)
        side.grid(row=0, column=1, sticky="nsew")

        true_clues = ["WE", "_7HE", "_B3ST"]
        decoys = ["PWN", "404", "NULL", "FAKE", "TRASH", "L0L"]
        found: set[str] = set()
        clue_var = tk.StringVar(value="Progress: [ ? ][ ? ][ ? ]")
        status_var = tk.StringVar(value="Click blocks to reveal clues.")
        attempts_var = tk.StringVar(value="Wrong picks this round: 0/4")
        round_var = tk.StringVar(value="Round: 1")
        helper_hint_var = tk.StringVar(value="Clue: The final flag starts with DOOM{WE...")
        wrong_picks = {"count": 0}
        round_count = {"value": 1}
        hint_steps = [
            "Clue: Middle fragment contains 7 replacing T.",
            "Clue: Ending fragment looks like _B3ST.",
            "Clue: Combine exactly as WE + _7HE + _B3ST.",
        ]

        def render_progress() -> None:
            ordered = [item if item in found else "?" for item in true_clues]
            clue_var.set(f"Progress: [ {ordered[0]} ][ {ordered[1]} ][ {ordered[2]} ]")

        block_buttons: list[tk.Button] = []

        def setup_round() -> None:
            found.clear()
            wrong_picks["count"] = 0
            attempts_var.set("Wrong picks this round: 0/4")
            round_var.set(f"Round: {round_count['value']}")
            status_var.set("New shuffled board loaded. Find all true clues.")
            helper_hint_var.set("Clue: The final flag starts with DOOM{WE...")
            render_progress()

            cell_items = true_clues + decoys
            random.shuffle(cell_items)
            for idx, btn in enumerate(block_buttons):
                item = cell_items[idx]
                btn.config(
                    text=f"BLOCK {idx + 1}",
                    state="normal",
                    bg="#2B3440",
                    fg="#FFFFFF",
                    command=lambda i=item, b=btn: click_block(b, i),
                )

        def click_block(btn: tk.Button, item: str) -> None:
            btn.config(state="disabled")
            if item in true_clues:
                found.add(item)
                btn.config(text=f"CLUE: {item}", bg="#1F6A3A", fg="#FFFFFF")
                status_var.set(f"Real clue found: {item}")
            else:
                self._play_sfx("wrong")
                btn.config(text=f"DECOY: {item}", bg="#4A1E1E", fg="#FFFFFF")
                wrong_picks["count"] += 1
                attempts_var.set(f"Wrong picks this round: {wrong_picks['count']}/4")
                hint_idx = min(wrong_picks["count"] - 1, len(hint_steps) - 1)
                helper_hint_var.set(hint_steps[hint_idx])
                status_var.set(f"Decoy found: {item}")
                if wrong_picks["count"] >= 4:
                    round_count["value"] += 1
                    messagebox.showwarning(
                        "Board Reset",
                        "4 wrong blocks pressed. Shuffling all blocks. Try again.",
                    )
                    setup_round()
                    return
            render_progress()

        for idx in range(9):
            row = idx // 3
            col = idx % 3
            block_btn = tk.Button(
                board,
                text=f"BLOCK {idx + 1}",
                font=("Consolas", 11, "bold"),
                fg="#FFFFFF",
                bg="#2B3440",
                activebackground="#3A4554",
                relief="raised",
                padx=8,
                pady=10,
                command=lambda: None,
            )
            block_btn.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            block_buttons.append(block_btn)

        for r in range(3):
            board.rowconfigure(r, weight=1)
        for c in range(3):
            board.columnconfigure(c, weight=1)

        ttk.Label(side, textvariable=clue_var, style="Body.TLabel", wraplength=260, justify="left").pack(anchor="w")
        ttk.Label(side, textvariable=status_var, style="Body.TLabel", wraplength=260, justify="left").pack(
            anchor="w", pady=(8, 8)
        )
        ttk.Label(side, textvariable=helper_hint_var, style="Body.TLabel", wraplength=260, justify="left").pack(
            anchor="w", pady=(0, 8)
        )
        ttk.Label(side, textvariable=attempts_var, style="Body.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(side, textvariable=round_var, style="Body.TLabel").pack(anchor="w", pady=(0, 10))

        ttk.Label(side, text="Build final flag:", style="Body.TLabel").pack(anchor="w")
        answer_var = tk.StringVar()
        entry = tk.Entry(
            side,
            textvariable=answer_var,
            width=28,
            font=("Consolas", 11),
            fg="#FFFFFF",
            bg="#0A0F14",
            insertbackground="#8AE234",
            relief="solid",
            highlightthickness=1,
            highlightbackground="#D70A53",
            highlightcolor="#D70A53",
        )
        entry.pack(anchor="w", pady=(6, 8))
        entry.focus_set()

        def submit_xhard() -> None:
            self.level_submit_counts["XHARD"] = self.level_submit_counts.get("XHARD", 0) + 1
            guess = answer_var.get().strip().upper()
            expected = str(data["expected"]).upper()
            if len(found) < len(true_clues):
                status_var.set("Find all 3 real clues first before submitting.")
                return
            if guess == expected:
                self._play_sfx("correct")
                messagebox.showinfo("XHARD Cleared", "Block puzzle solved. Correct flag assembled.")
                self._complete_level("XHARD")
                if win.winfo_exists():
                    win.destroy()
                return
            self._play_sfx("wrong")
            status_var.set("Incorrect flag. Re-check real clues and order.")

        ttk.Button(side, text="Submit Flag", style="Game.TButton", command=submit_xhard).pack(anchor="w")
        entry.bind("<Return>", lambda _event: submit_xhard())
        setup_round()

    def _open_crazy_reaction_game(self) -> None:
        if self.challenge_window is not None and self.challenge_window.winfo_exists():
            self.challenge_window.destroy()
            self._stop_timer()

        self.active_level = "CRAZY"
        self.level_start_time["CRAZY"] = time.perf_counter()
        self.level_submit_counts["CRAZY"] = 0
        data = self.levels["CRAZY"]

        win = tk.Toplevel(self.root)
        win.title("Challenge - CRAZY")
        win.geometry("780x520")
        win.configure(bg=self.colors["bg"])
        self.challenge_window = win

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="CRAZY - REACTION CORE", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text=data["desc"], style="SubTitle.TLabel").pack(anchor="w", pady=(4, 10))

        info_text = (
            "Story: The core lock opens only at 6.7 seconds.\n"
            "Rules: Press START, wait, then STOP as close as possible to 6.7s.\n"
            "Clear zone: +/-0.12 seconds."
        )
        ttk.Label(frame, text=info_text, style="Body.TLabel", justify="left").pack(anchor="w", pady=(0, 12))

        elapsed_var = tk.StringVar(value="0.00 s")
        result_var = tk.StringVar(value="Press START to begin.")

        tk.Label(
            frame,
            textvariable=elapsed_var,
            font=("Consolas", 40, "bold"),
            fg="#8AE234",
            bg=self.colors["bg"],
        ).pack(anchor="center", pady=(10, 16))

        running = {"value": False}
        start_time = {"value": 0.0}
        tick_job = {"id": None}
        target = 6.7
        tolerance = 0.12

        def stop_tick() -> None:
            if tick_job["id"] is not None:
                try:
                    win.after_cancel(tick_job["id"])
                except Exception:
                    pass
                tick_job["id"] = None

        def tick_clock() -> None:
            if not running["value"] or not win.winfo_exists():
                return
            current = time.perf_counter() - start_time["value"]
            elapsed_var.set(f"{current:.2f} s")
            tick_job["id"] = win.after(20, tick_clock)

        def start_game() -> None:
            running["value"] = True
            start_time["value"] = time.perf_counter()
            result_var.set("Timer running... click STOP at 6.7s")
            start_btn.config(state="disabled")
            stop_btn.config(state="normal")
            tick_clock()

        def stop_game() -> None:
            if not running["value"]:
                return
            self.level_submit_counts["CRAZY"] = self.level_submit_counts.get("CRAZY", 0) + 1
            running["value"] = False
            stop_tick()
            elapsed = time.perf_counter() - start_time["value"]
            elapsed_var.set(f"{elapsed:.2f} s")

            diff = abs(elapsed - target)
            if diff <= tolerance:
                result_var.set(f"Perfect zone hit! diff={diff:.3f}s -> Flag unlocked")
                self._play_sfx("celebrate")
                self._show_crazy_celebration()
                messagebox.showinfo("CRAZY Cleared", f"Flag unlocked: {data['expected']}")
                self._complete_level("CRAZY")
                if win.winfo_exists():
                    win.destroy()
                return

            self._play_sfx("wrong")
            result_var.set(f"Missed by {diff:.3f}s. Retry and hit 6.7!")
            start_btn.config(state="normal")
            stop_btn.config(state="disabled")

        controls = ttk.Frame(frame)
        controls.pack(anchor="center", pady=(0, 12))
        start_btn = ttk.Button(controls, text="START", style="Game.TButton", command=start_game)
        start_btn.pack(side="left", padx=(0, 8))
        stop_btn = ttk.Button(controls, text="STOP", style="Game.TButton", command=stop_game)
        stop_btn.pack(side="left")
        stop_btn.config(state="disabled")

        ttk.Label(frame, textvariable=result_var, style="Body.TLabel", justify="left").pack(anchor="w")

        def on_close() -> None:
            running["value"] = False
            stop_tick()
            if win.winfo_exists():
                win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def _show_crazy_celebration(self) -> None:
        popup = tk.Toplevel(self.root)
        popup.title("CRAZY MODE CLEAR")
        popup.geometry("560x300")
        popup.configure(bg="#120814")
        popup.transient(self.root)
        popup.grab_set()

        frame = tk.Frame(popup, bg="#120814", highlightbackground="#FF2E88", highlightthickness=3)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        text_var = tk.StringVar(value="WOAHHH 6 7")
        subtitle_var = tk.StringVar(value="BRAINROT REACTION KING")

        title_lbl = tk.Label(
            frame,
            textvariable=text_var,
            font=("Consolas", 34, "bold"),
            fg="#F8FF5A",
            bg="#120814",
        )
        title_lbl.pack(pady=(40, 8))

        sub_lbl = tk.Label(
            frame,
            textvariable=subtitle_var,
            font=("Consolas", 14, "bold"),
            fg="#8AE234",
            bg="#120814",
        )
        sub_lbl.pack()

        pulses = [
            ("WOAHHH 6 7", "#F8FF5A", "#120814"),
            ("WOAHHH SIX SEVEN", "#00F5FF", "#1A1030"),
            ("67 TREND UNLOCKED", "#FF7B00", "#1F0C12"),
            ("BRAINROT MODE", "#8AE234", "#101A10"),
        ]
        state = {"idx": 0, "ticks": 0}

        def animate() -> None:
            if not popup.winfo_exists():
                return
            msg, fg, bg = pulses[state["idx"]]
            text_var.set(msg)
            title_lbl.config(fg=fg, bg=bg)
            sub_lbl.config(bg=bg)
            frame.config(bg=bg)
            popup.config(bg=bg)
            state["idx"] = (state["idx"] + 1) % len(pulses)
            state["ticks"] += 1
            if state["ticks"] >= 12:
                popup.destroy()
                return
            popup.after(140, animate)

        animate()
        popup.wait_window()

    def _set_side_panel(self, text: str) -> None:
        if self.side_info_box is None:
            return
        self.side_info_box.config(state="normal")
        self.side_info_box.delete("1.0", "end")
        self.side_info_box.insert("1.0", text)
        self.side_info_box.config(state="disabled")

    def submit_answer(self) -> None:
        if not self.active_level:
            return

        data = self.levels[self.active_level]
        self.level_submit_counts[self.active_level] = self.level_submit_counts.get(self.active_level, 0) + 1
        user_answer = self.answer_var.get().strip().upper()
        expected = str(data["expected"]).upper()

        if user_answer == expected:
            self._stop_timer()
            self._play_sfx("correct")
            self._complete_level(self.active_level)
            self.feedback_var.set("Correct. Level cleared.")
            messagebox.showinfo("Correct", f"{self.active_level} cleared! +{data['points']} points")
            return

        self._play_sfx("wrong")
        self.attempts_left -= 1
        if self.active_level == "DOOMDADA":
            self.doomdada_attempts_left = self.attempts_left
        self._refresh_attempt_label()

        if self.active_level == "DOOMDADA":
            self._handle_doomdada_failure()
            return

        if self.attempts_left > 0:
            self.feedback_var.set("Incorrect. Use 'Need Help?' for a simpler clue.")
            return

        self.feedback_var.set(f"No attempts left. Answer: {data['expected']}")
        self._stop_timer()
        messagebox.showwarning("Out of Attempts", f"Answer: {data['expected']}")

    def _handle_doomdada_failure(self) -> None:
        if self.attempts_left == 2:
            if self.challenge_window and self.challenge_window.winfo_exists():
                self.challenge_window.configure(bg="#251016")
            if self.doomdada_alert_bar and self.doomdada_alert_bar.winfo_exists():
                self.doomdada_alert_bar.config(
                    text="[ DOOMDADA MONITOR ] Threat level: ELEVATED",
                    bg="#3A1E10",
                    fg="#FDE68A",
                )
            warning_text = (
                "[WARNING BLOCK 1]\n\n"
                "Simulated threat detected in DOOMDADA zone.\n"
                "One more mistake will increase system lockdown level.\n"
                f"Attempts remaining: {self.attempts_left}"
            )
            self.feedback_var.set("DOOMDADA security warning triggered (Level 1).")
            self._set_side_panel(warning_text)
            messagebox.showwarning("DOOMDADA ALERT", warning_text)
            return

        if self.attempts_left == 1:
            if self.challenge_window and self.challenge_window.winfo_exists():
                self.challenge_window.configure(bg="#331013")
            if self.doomdada_alert_bar and self.doomdada_alert_bar.winfo_exists():
                self.doomdada_alert_bar.config(
                    text="[ DOOMDADA MONITOR ] Threat level: CRITICAL",
                    bg="#4A1218",
                    fg="#FCA5A5",
                )
            warning_text = (
                "[WARNING BLOCK 2]\n\n"
                "Simulated virus firewall activated.\n"
                "Final attempt remaining before forced lockdown.\n"
                f"Attempts remaining: {self.attempts_left}"
            )
            self.feedback_var.set("DOOMDADA security warning triggered (Level 2).")
            self._set_side_panel(warning_text)
            messagebox.showwarning("DOOMDADA ALERT", warning_text)
            return

        lockdown_text = (
            "[SYSTEM LOCKDOWN]\n\n"
            "DOOMDADA protocol triggered a full shutdown simulation.\n"
            "Progress has been reset. Restart from Easy to Hard."
        )
        self.feedback_var.set("Lockdown triggered. Progress reset.")
        self._play_sfx("lockdown")
        self._set_side_panel(lockdown_text)
        self._stop_timer()
        self._reset_progress_silent()
        if self.classroom_mode_var.get():
            messagebox.showwarning(
                "CLASSROOM LOCKDOWN",
                lockdown_text + "\n\nClassroom Mode is ON, so the app will stay open.",
            )
            return
        self._show_lockdown_overlay(lockdown_text)

    def _show_lockdown_overlay(self, lockdown_text: str) -> None:
        self.root.update_idletasks()

        if self.challenge_window and self.challenge_window.winfo_exists():
            self.challenge_window.destroy()

        overlay = tk.Toplevel(self.root)
        overlay.title("LOCKDOWN MODE")
        overlay.configure(bg="#120000")
        overlay.attributes("-topmost", True)

        width = max(self.root.winfo_width(), 900)
        height = max(self.root.winfo_height(), 600)
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        overlay.geometry(f"{width}x{height}+{x}+{y}")

        container = tk.Frame(overlay, bg="#120000", highlightbackground="#FF1E1E", highlightthickness=3)
        container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.8)

        tk.Label(
            container,
            text="[ LOCKDOWN MODE ACTIVATED ]",
            font=("Consolas", 28, "bold"),
            fg="#FF2D2D",
            bg="#120000",
        ).pack(pady=(40, 20))

        tk.Label(
            container,
            text="SIMULATED THREAT RESPONSE: SYSTEM QUARANTINE",
            font=("Consolas", 14, "bold"),
            fg="#FF7B7B",
            bg="#120000",
        ).pack(pady=(0, 20))

        details = tk.Text(
            container,
            wrap="word",
            font=("Consolas", 12),
            bg="#1A0000",
            fg="#FFD1D1",
            relief="flat",
            height=8,
        )
        details.insert("1.0", lockdown_text + "\n\nSystem will close now...")
        details.config(state="disabled")
        details.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        self.root.after(2200, self.root.destroy)

    def show_next_hint(self) -> None:
        if not self.active_level:
            return
        self.level_hint_used.add(self.active_level)
        data = self.levels[self.active_level]
        hints = data.get("hints", [])
        if not hints:
            self.feedback_var.set("No extra hints for this level.")
            self._set_side_panel("No extra hints for this level.")
            return
        if self.hint_index >= len(hints):
            self.feedback_var.set("No more hints. Try using previous clues.")
            self._set_side_panel("No more hints available. Recheck previous hints and walkthrough.")
            return
        hint_text = f"Hint {self.hint_index + 1}: {hints[self.hint_index]}"
        self.feedback_var.set(hint_text)
        self._set_side_panel(hint_text)
        self.hint_index += 1

    def show_walkthrough(self) -> None:
        if not self.active_level:
            return
        data = self.levels[self.active_level]
        walkthrough = data.get("walkthrough", "No walkthrough available.")
        self._set_side_panel(str(walkthrough))

    def show_real_world(self) -> None:
        if not self.active_level:
            return
        data = self.levels[self.active_level]
        why = data.get("real_world", "This puzzle trains logic and precision.")
        self._set_side_panel(f"Why It Matters\n\n{why}")

    def show_common_mistakes(self) -> None:
        if not self.active_level:
            return
        data = self.levels[self.active_level]
        mistakes = data.get("common_mistakes", ["No common mistakes listed."])
        text = "Common Mistakes\n\n" + "\n".join(f"- {item}" for item in mistakes)
        self._set_side_panel(text)

    def show_presenter_script(self) -> None:
        if not self.active_level:
            return
        data = self.levels[self.active_level]
        script = data.get("presenter_script", "No presenter script available.")
        self._set_side_panel(str(script))

    def show_python_cheatsheet(self) -> None:
        cheatsheet = (
            "Python Cheatsheet\n\n"
            "def name(args):\n"
            "    return value\n\n"
            "for i, ch in enumerate(text):\n"
            "    print(i, ch)\n\n"
            "table.get(key, default)  # safe dictionary lookup\n"
            "''.join(items)           # combine list of chars into one string\n"
            "f\"DOOM{{{value}}}\"      # format a flag string"
        )
        self._set_side_panel(cheatsheet)

    def show_function_purpose(self) -> None:
        if self.active_level == "DOOMDADA":
            text = (
                "Function Purpose (DOOMDADA)\n\n"
                "story_seed() -> gives original phrase\n"
                "apply_leet(text) -> swaps letters to symbols\n"
                "apply_case_pattern(text) -> sets uppercase/lowercase pattern\n"
                "build_flag() -> combines all steps and wraps with DOOM{...}"
            )
        else:
            text = (
                "Function Purpose\n\n"
                "Use helper functions to break big problems into small steps.\n"
                "Define input -> transform -> output, then verify final format."
            )
        self._set_side_panel(text)

    def insert_starter_snippet(self, kind: str) -> None:
        if self.console_input is None:
            return
        snippets = {
            "base": "phrase = story_seed()\nprint(phrase)\n",
            "leet": "phrase = story_seed()\nstage1 = apply_leet(phrase)\nprint(stage1)\n",
            "case": "phrase = story_seed()\nstage1 = apply_leet(phrase)\nstage2 = apply_case_pattern(stage1)\nprint(stage2)\n",
            "build": "result = build_flag()\nprint(result)\n",
        }
        snippet = snippets.get(kind, "")
        if not snippet:
            return
        self.console_input.delete("1.0", "end")
        self.console_input.insert("1.0", snippet)
        if self.console_output_var is not None:
            self.console_output_var.set("Console: starter code inserted")

    def clear_console(self) -> None:
        if self.console_input is not None:
            self.console_input.delete("1.0", "end")
        if self.console_output_var is not None:
            self.console_output_var.set("Console: cleared")

    def _get_console_env(self) -> dict[str, object]:
        expected = self.levels[self.active_level]["expected"] if self.active_level else ""

        def check_flag(value: object) -> bool:
            return str(value).strip() == str(expected)

        env: dict[str, object] = {
            "expected_flag": expected,
            "check_flag": check_flag,
        }

        if self.active_level == "DOOMDADA":
            def story_seed() -> str:
                return "congratulations!"

            def apply_leet(text: str) -> str:
                table = {"o": "0", "g": "6", "a": "@", "t": "+", "s": "$"}
                return "".join(table.get(ch, ch) for ch in text.lower())

            def apply_case_pattern(text: str) -> str:
                upper_idx = {0, 7, 8, 10, 12}
                out = []
                for i, ch in enumerate(text):
                    out.append(ch.upper() if i in upper_idx else ch.lower())
                return "".join(out).replace("@", "4")

            def build_flag() -> str:
                stage2 = apply_case_pattern(apply_leet(story_seed()))
                return f"DOOM{{{stage2}}}"

            env.update(
                {
                    "story_seed": story_seed,
                    "apply_leet": apply_leet,
                    "apply_case_pattern": apply_case_pattern,
                    "build_flag": build_flag,
                }
            )

        return env

    def run_console_code(self) -> None:
        if self.console_input is None or self.console_output_var is None:
            return

        source = self.console_input.get("1.0", "end").strip()
        if not source:
            self.console_output_var.set("Console: no code to run")
            return

        safe_builtins = {
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "range": range,
            "enumerate": enumerate,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "sum": sum,
            "min": min,
            "max": max,
        }

        env = self._get_console_env()
        stdout = io.StringIO()
        result_obj: object | None = None

        try:
            with contextlib.redirect_stdout(stdout):
                try:
                    compiled = compile(source, "<mini-console>", "eval")
                    result_obj = eval(compiled, {"__builtins__": safe_builtins}, env)
                except SyntaxError:
                    compiled = compile(source, "<mini-console>", "exec")
                    exec(compiled, {"__builtins__": safe_builtins}, env)
        except Exception as exc:
            self.console_output_var.set(f"Console error: {exc}")
            return

        printed = stdout.getvalue().strip()
        candidate = ""
        if result_obj is not None:
            candidate = str(result_obj).strip()
        elif isinstance(env.get("flag"), str):
            candidate = str(env["flag"]).strip()
        elif isinstance(env.get("result"), str):
            candidate = str(env["result"]).strip()
        elif printed:
            candidate = printed.splitlines()[-1].strip()

        expected = str(self.levels[self.active_level]["expected"]) if self.active_level else ""
        funny_flags = ["DOOM{imtheflag}", "DOOM{whats9+10?}", "DOOM{almostthere}"]

        if candidate and candidate == expected:
            self.console_output_var.set(f"Console verdict: MATCH -> {candidate}")
            self._set_side_panel(f"Console Output\n\n{printed or candidate}\n\nVerdict: Correct flag.")
        else:
            fake = random.choice(funny_flags)
            shown = candidate if candidate else "(no flag output detected)"
            self.console_output_var.set(f"Console verdict: not matched -> {fake}")
            self._set_side_panel(
                f"Console Output\n\n{printed or shown}\n\nExpected format check failed. Try again.\nFun fake flag: {fake}"
            )

    def show_trace_table(self) -> None:
        if not self.active_level:
            return
        data = self.levels[self.active_level]
        trace = data.get(
            "trace_table",
            "Trace table is currently available for DOOMDADA only.",
        )
        self._set_side_panel(str(trace))

    def _play_sfx(self, event_type: str) -> None:
        if self.mute_sfx_var.get():
            return
        try:
            if winsound is not None:
                tones = {
                    "correct": [(880, 90), (1175, 120)],
                    "wrong": [(300, 110)],
                    "lockdown": [(220, 140), (180, 220)],
                    "celebrate": [(900, 80), (1100, 80), (1320, 120)],
                }
                for freq, dur in tones.get(event_type, []):
                    winsound.Beep(freq, dur)
                if event_type not in tones:
                    self.root.bell()
            else:
                self.root.bell()
        except Exception:
            self.root.bell()

    def _compute_achievements(self, level_name: str) -> list[str]:
        badges: list[str] = []
        attempts = self.level_submit_counts.get(level_name, 0)
        if attempts == 1:
            badges.append("First Try")
        if level_name not in self.level_hint_used:
            badges.append("No Hint")

        start = self.level_start_time.get(level_name)
        target = self.level_speed_targets.get(level_name)
        if start is not None and target is not None:
            elapsed = time.perf_counter() - start
            if elapsed <= target:
                badges.append(f"Speedrun ({elapsed:.1f}s)")
        return badges

    def _complete_level(self, level_name: str) -> None:
        data = self.levels[level_name]
        if level_name not in self.completed_levels:
            self.total_score += int(data["points"])
            self.completed_levels.add(level_name)
            self._award_team_points(int(data["points"]))
        if level_name == "DOOMDADA":
            self.doomdada_attempts_left = 3
        self._refresh_status()

        teacher_script = data.get("teacher_script", "We applied the puzzle rule correctly.")
        student_takeaway = data.get("student_takeaway", "Use step-by-step reasoning for better accuracy.")
        recap_text = (
            f"Teacher Script: {teacher_script}\n\n"
            f"Student Takeaway: {student_takeaway}"
        )
        messagebox.showinfo(f"Recap - {level_name}", recap_text)
        self._show_level_debrief(level_name, data)
        badges = self._compute_achievements(level_name)
        self.level_achievements[level_name] = badges
        if badges:
            messagebox.showinfo("Badges Unlocked", f"{level_name}: " + ", ".join(badges))
        self._maybe_show_end_credits()

    def _maybe_show_end_credits(self) -> None:
        if len(self.completed_levels) != len(self.levels) or self.end_credits_shown:
            return
        self.end_credits_shown = True
        credits = (
            "End Credits\n\n"
            "RANDOM AHH GAME by DOOMDADA\n"
            "Story Arc Completed: Easy -> Medium -> Hard -> XHARD -> CRAZY -> DOOMDADA\n\n"
            "Thanks for playing and thinking like a reverse engineer."
        )
        messagebox.showinfo("End Credits", credits)


def main() -> None:
    root = tk.Tk()
    ReverseEngineeringGameGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
