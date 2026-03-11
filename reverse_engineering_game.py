#!/usr/bin/env python3
"""
Reverse Engineering Bootcamp Game
Interactive CLI game for webinar engagement.
"""

from __future__ import annotations

import textwrap


def clear_line() -> None:
    print("-" * 72)


def banner() -> None:
    print(
        r"""
 ____                                 _____             _
|  _ \ ___  __ _  ___ _ __ ___  ___  | ____|_ __   __ _(_)_ __   ___
| |_) / _ \/ _` |/ __| '__/ _ \/ __| |  _| | '_ \ / _` | | '_ \ / _ \
|  _ <  __/ (_| | (__| | |  __/\__ \ | |___| | | | (_| | | | | |  __/
|_| \_\___|\__,_|\___|_|  \___||___/ |_____|_| |_|\__, |_|_| |_|\___|
                                                   |___/
"""
    )
    print("Reverse Engineering Game - Webinar Edition")
    print("Difficulty: Easy | Medium | Hard | DOOMDADA")
    clear_line()


def about_reverse_engineering() -> None:
    clear_line()
    print("What is Reverse Engineering (Rev.Eng)?")
    print(
        textwrap.fill(
            "Reverse engineering is the process of analyzing compiled software, "
            "binaries, protocols, or hardware to understand how they work "
            "without having the original source code.",
            width=72,
        )
    )
    print()
    print("What does it do?")
    print("- Reveals hidden program logic")
    print("- Helps analysts inspect input checks, encryption, and behavior")
    print("- Supports malware analysis and software security audits")
    print()
    print("What is its purpose?")
    print("- Improve security by finding weaknesses")
    print("- Verify software behavior and trust claims")
    print("- Train problem-solving for cybersecurity and CTF challenges")
    print()
    print("Use RE ethically: only in legal and authorized environments.")
    clear_line()


def how_to_play() -> None:
    clear_line()
    print("How to Play")
    print("1. Pick a level from Easy to DOOMDADA.")
    print("2. Read the pseudo-code/disassembly challenge.")
    print("3. Compute the answer and type it in.")
    print("4. You get up to 3 tries per level.")
    print("5. Correct answer gives points and a short explanation.")
    print()
    print("Scoring")
    print("- Easy: 50 points")
    print("- Medium: 100 points")
    print("- Hard: 150 points")
    print("- DOOMDADA: 200 points")
    print()
    print("Tip: Think like an analyst. Break each operation step-by-step.")
    print("Need extra help? Use 'Beginner Tutorial' from the main menu.")
    clear_line()


def beginner_tutorial() -> None:
    clear_line()
    print("Beginner Tutorial (No Python Background Needed)")
    print()
    print("How to read these challenges:")
    print("1. Treat code lines like calculator instructions.")
    print("2. Execute one line at a time from top to bottom.")
    print("3. Write intermediate values on paper as you go.")
    print()
    print("Quick symbol guide:")
    print("- '=' means set/assign a value")
    print("- '+' means add")
    print("- '^' means XOR (bitwise compare)")
    print("- '%' means remainder/modulo")
    print("- 'for (...)' means repeat steps")
    print()
    print("Mini example:")
    print("mov eax, 0x2A -> start with 42")
    print("imul eax, eax, 3 -> multiply by 3 (126)")
    print("sub eax, 0x15 -> subtract 21 (105)")
    print("xor eax, 0x5 -> final transformed value")
    print()
    print("You do not need to code. Just follow logic step-by-step.")
    clear_line()


def ask_with_attempts(
    prompt: str,
    expected: str,
    attempts: int = 3,
    case_sensitive: bool = False,
    hints: list[str] | None = None,
) -> bool:
    for turn in range(1, attempts + 1):
        user_input = input(f"Try {turn}/{attempts} -> {prompt}").strip()
        left = user_input if case_sensitive else user_input.upper()
        right = expected if case_sensitive else expected.upper()
        if left == right:
            return True
        print("Not quite. Analyze the operations again.")
        if hints and turn - 1 < len(hints):
            print(f"Hint: {hints[turn - 1]}")
    return False


def level_easy() -> int:
    clear_line()
    print("[EASY] Puzzle Quest - Warm-up Word")
    print("Unscramble the letters to get the keyword.")
    print()
    print("Puzzle letters: PMTOOCBA")
    print("Rule: submit as DOOM{WORD}")
    print()

    easy_hints = [
        "XOR can be reversed by XOR-ing with the same value again.",
        "Take each target hex byte and XOR it with 0x13.",
        "The decoded text spells a bootcamp-related word.",
    ]

    if ask_with_attempts("Flag (DOOM{...}): ", "DOOM{BOOTCAMP}", hints=easy_hints):
        print("Correct. XOR each target byte with 0x13 to decode ASCII.")
        return 50
    print("Answer: DOOM{BOOTCAMP}")
    return 0


def level_medium() -> int:
    clear_line()
    print("[MEDIUM] Cipher Quest - Leet Upgrade")
    print("Transform the base phrase using simple rules.")
    print()
    print("Base phrase: EARLYBIRD")
    print("Rules: replace E->3 and I->1")
    print("Submit exactly with inner quotes.")
    print()

    medium_hints = [
        "0x2A is 42 in decimal and 0x15 is 21.",
        "Compute math first, then apply XOR with 5.",
        'Use the custom flag exactly: DOOM{"3ARLYB1RD"}.',
    ]

    if ask_with_attempts("Flag (DOOM{...}): ", 'DOOM{"3ARLYB1RD"}', hints=medium_hints):
        print("Correct. Trace each arithmetic step in order.")
        return 100
    print('Answer: DOOM{"3ARLYB1RD"}')
    return 0


def level_hard() -> int:
    clear_line()
    print("[HARD] Pattern Quest - Case Mask")
    print("Apply capitalization pattern to a base word.")
    print()
    print("Base: ambatukammm")
    print("Mask (1-based): capitalize #1, #3, and #6")
    print("Submit exactly with inner quotes.")
    print()

    hard_hints = [
        "You can ignore implementation details and focus on the final expected flag.",
        "This level's answer is a phrase-style custom flag with inner quotes.",
        'Use exact casing and punctuation: DOOM{"AmBatUkammm"}.',
    ]

    if ask_with_attempts("Flag (DOOM{...}): ", 'DOOM{"AmBatUkammm"}', hints=hard_hints):
        print("Correct. Good decompilation math and operator tracing.")
        return 150
    print('Answer: DOOM{"AmBatUkammm"}')
    return 0


def level_doomdada() -> int:
    clear_line()
    print("[DOOMDADA] Final Boss - Celebratory Phrase Recovery")
    print("Recover the final transformed phrase and submit it as a flag.")
    print()
    print("name = \"DOOMDADA\"")
    print("acc = 0")
    print("for (i = 0; i < len(name); i++) {")
    print("    acc += (ord(name[i]) ^ (0x21 + i)) * (i + 3)")
    print("}")
    print("acc = ((acc << 1) ^ 0xBEEF) & 0xFFFF")
    print("phrase = \"congratulations!\"")
    print("leet = {\"o\":\"0\",\"g\":\"6\",\"a\":\"4\",\"t\":\"+\",\"s\":\"$\"}")
    print("for each char in phrase: replace using leet map when possible")
    print("preserve mixed casing pattern: C0n6r@+Ul4tIoN$!")
    print()
    print("Example format: DOOM{...}")
    print()

    doomdada_hints = [
        "The target phrase is a l33t-styled version of 'congratulations!'.",
        "Preserve the exact mixed casing shown in the prompt.",
        "Copy the exact final flag pattern from the clue line.",
    ]

    if ask_with_attempts("Flag (DOOM{...}): ", "DOOM{C0n6r@+Ul4tIoN$!}", hints=doomdada_hints):
        print("Legendary. You completed the hardest tier.")
        return 200
    print("Answer: DOOM{C0n6r@+Ul4tIoN$!}")
    return 0


def play_game() -> None:
    levels = {
        "1": ("Easy", level_easy),
        "2": ("Medium", level_medium),
        "3": ("Hard", level_hard),
        "4": ("DOOMDADA", level_doomdada),
    }

    total_score = 0
    finished = set()

    while True:
        clear_line()
        print("Select a level")
        print("1) Easy")
        print("2) Medium")
        print("3) Hard")
        print("4) DOOMDADA")
        print("5) Show Score")
        print("6) Return to Main Menu")

        choice = input("Choice: ").strip()

        if choice in levels:
            label, fn = levels[choice]
            gained = fn()
            total_score += gained
            finished.add(label)
        elif choice == "5":
            clear_line()
            print(f"Current score: {total_score}")
            print("Completed levels: " + (", ".join(sorted(finished)) if finished else "None"))
            if len(finished) == 4:
                print("All levels cleared. Webinar champion unlocked.")
            clear_line()
        elif choice == "6":
            break
        else:
            print("Invalid choice. Select 1-6.")


def main() -> None:
    banner()
    while True:
        print("Main Menu")
        print("1) What is Reverse Engineering?")
        print("2) How to Play")
        print("3) Beginner Tutorial")
        print("4) Start Game")
        print("5) Exit")

        choice = input("Choice: ").strip()

        if choice == "1":
            about_reverse_engineering()
        elif choice == "2":
            how_to_play()
        elif choice == "3":
            beginner_tutorial()
        elif choice == "4":
            play_game()
        elif choice == "5":
            print("Thanks for playing. Good luck in your webinar.")
            break
        else:
            print("Invalid choice. Select 1-5.")


if __name__ == "__main__":
    main()
