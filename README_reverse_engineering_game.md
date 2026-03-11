# Reverse Engineering Webinar Game

## Files
- `reverse_engineering_game.py` - Interactive game app
- `reverse_engineering_game_gui.py` - Polished GUI app (buttons/windows)
- `reverse_engineering_bootcamp.md` - Topic notes and challenge set

## Run the Game (Windows)
From the workspace folder, run:

```powershell
C:/Users/johnh/AppData/Local/Microsoft/WindowsApps/python3.11.exe reverse_engineering_game.py
```

If `python` works in your terminal, this also works:

```powershell
python reverse_engineering_game.py
```

## Run the GUI Version (Recommended for Webinar)

```powershell
C:/Users/johnh/AppData/Local/Microsoft/WindowsApps/python3.11.exe reverse_engineering_game_gui.py
```

Or:

```powershell
python reverse_engineering_game_gui.py
```

## What the App Includes
- Explanation of reverse engineering
- Purpose and legal/ethical context
- How to play section
- Beginner tutorial for non-Python audiences
- 4 playable levels:
  - Easy
  - Medium
  - Hard
  - DOOMDADA (hardest)
- Score tracking and completion summary
- Optional timed mode (60s per challenge)
- Built-in leaderboard with score submission
- Progressive hint system (plain-language clues)
- One-click walkthrough per level (GUI)
- Presenter script popup per level (GUI)

## Gameplay Format
- 3 attempts per level
- Correct answer awards points
- Can replay levels and check score any time
- Optional timed mode adds urgency for live audience participation
- Leaderboard saves top scores to `leaderboard.json`

## Presenter Tip
Open a terminal side-by-side with the script output so your webinar audience can watch you solve levels live.

For screen-sharing, prefer the GUI version because it is easier for viewers to follow interactions and scores.
