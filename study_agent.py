"""
Study Agent — turns lecture notes into a study plan, quizzes,
and flashcards, and tracks your progress over time.

Usage:
    python study_agent.py add notes.txt          -> process new notes
    python study_agent.py plan                   -> show/update study plan
    python study_agent.py quiz                    -> take a quiz on weak topics
    python study_agent.py flashcards               -> review flashcards
    python study_agent.py progress                 -> see your stats
"""

import os
import sys
import json
import random
from datetime import datetime
from groq import Groq

# ---------- SETUP ----------

API_KEY = os.environ.get("GROQ_API_KEY")
if not API_KEY:
    print("ERROR: Set your GROQ_API_KEY environment variable first.")
    print("  Mac/Linux:  export GROQ_API_KEY='your-key-here'")
    print("  Windows:    setx GROQ_API_KEY \"your-key-here\"")
    sys.exit(1)

client = Groq(api_key=API_KEY)
MODEL = "llama-3.3-70b-versatile"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "study_data.json")


# ---------- DATA STORAGE ----------

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {"topics": {}, "history": []}


def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)


# ---------- AI HELPERS ----------

def ask_ai(system_prompt, user_prompt, json_mode=False):
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        **kwargs,
    )
    return response.choices[0].message.content


def process_notes(notes_text):
    """Takes raw lecture notes and returns topic, summary, quiz, flashcards."""
    system = (
        "You are a study assistant. Given lecture notes, extract a single main "
        "topic name (2-4 words), a clear summary (150-250 words), 5 quiz questions "
        "(multiple choice, 4 options each, mark the correct one), and 8 flashcards "
        "(front/back). Respond ONLY in valid JSON with this exact structure: "
        '{"topic": "...", "summary": "...", '
        '"quiz": [{"question": "...", "options": ["a","b","c","d"], "answer": "a"}], '
        '"flashcards": [{"front": "...", "back": "..."}]}'
    )
    result = ask_ai(system, notes_text, json_mode=True)
    return json.loads(result)


def generate_study_plan(db):
    """Builds a prioritized study plan based on weak topics."""
    topics = db["topics"]
    if not topics:
        return "No topics yet. Add some notes first with: python study_agent.py add <file>"

    topic_summary = []
    for name, t in topics.items():
        accuracy = t["correct"] / t["attempts"] if t["attempts"] > 0 else None
        topic_summary.append({
            "topic": name,
            "accuracy": round(accuracy, 2) if accuracy is not None else "not tested yet",
            "last_studied": t.get("last_studied", "never"),
        })

    system = (
        "You are a study coach. Given a list of topics with quiz accuracy and last "
        "studied date, create a short prioritized study plan (numbered list, max 6 "
        "items). Prioritize low accuracy and topics not studied recently. Be specific "
        "and encouraging. Keep it under 200 words."
    )
    plan = ask_ai(system, json.dumps(topic_summary))
    return plan


# ---------- COMMANDS ----------

def cmd_add(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, "r") as f:
        notes_text = f.read()

    print("Processing your notes with AI... (this takes a few seconds)")
    result = process_notes(notes_text)

    db = load_db()
    topic_name = result["topic"]

    db["topics"][topic_name] = {
        "summary": result["summary"],
        "quiz": result["quiz"],
        "flashcards": result["flashcards"],
        "attempts": db["topics"].get(topic_name, {}).get("attempts", 0),
        "correct": db["topics"].get(topic_name, {}).get("correct", 0),
        "last_studied": datetime.now().isoformat(),
        "added": datetime.now().isoformat(),
    }
    save_db(db)

    print(f"\nAdded topic: {topic_name}")
    print(f"\n--- SUMMARY ---\n{result['summary']}")
    print(f"\nGenerated {len(result['quiz'])} quiz questions and {len(result['flashcards'])} flashcards.")
    print("Run 'python study_agent.py plan' to see your study plan.")


def cmd_plan():
    db = load_db()
    plan = generate_study_plan(db)
    print("\n=== YOUR STUDY PLAN ===\n")
    print(plan)


def cmd_quiz():
    db = load_db()
    topics = db["topics"]
    if not topics:
        print("No topics yet. Add notes first.")
        return

    # Prioritize weakest topic
    def weakness(t):
        if t["attempts"] == 0:
            return -1
        return t["correct"] / t["attempts"]

    topic_name = min(topics, key=lambda k: weakness(topics[k]))
    topic = topics[topic_name]

    print(f"\n=== QUIZ: {topic_name} ===\n")
    correct_count = 0
    questions = topic["quiz"]
    random.shuffle(questions)

    for q in questions:
        print(q["question"])
        for i, opt in enumerate(q["options"]):
            print(f"  {chr(97+i)}) {opt}")
        ans = input("Your answer (a/b/c/d): ").strip().lower()
        correct_letter = q["answer"].strip().lower()[0]
        if ans == correct_letter:
            print("Correct!\n")
            correct_count += 1
        else:
            print(f"Incorrect. Correct answer: {q['answer']}\n")

    topic["attempts"] += len(questions)
    topic["correct"] += correct_count
    topic["last_studied"] = datetime.now().isoformat()
    db["history"].append({
        "date": datetime.now().isoformat(),
        "topic": topic_name,
        "score": f"{correct_count}/{len(questions)}",
    })
    save_db(db)

    print(f"Score: {correct_count}/{len(questions)}")


def cmd_flashcards():
    db = load_db()
    topics = db["topics"]
    if not topics:
        print("No topics yet. Add notes first.")
        return

    print("\nWhich topic?")
    names = list(topics.keys())
    for i, name in enumerate(names):
        print(f"  {i+1}) {name}")
    choice = input("Pick a number: ").strip()
    try:
        topic_name = names[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return

    cards = topics[topic_name]["flashcards"]
    random.shuffle(cards)

    print(f"\n=== FLASHCARDS: {topic_name} ===")
    print("(press Enter to flip, then 'n' for next)\n")
    for card in cards:
        input(f"Q: {card['front']}\n[Enter to reveal]")
        print(f"A: {card['back']}\n")
        input("[Enter for next card]\n")


def cmd_progress():
    db = load_db()
    topics = db["topics"]
    if not topics:
        print("No data yet.")
        return

    print("\n=== YOUR PROGRESS ===\n")
    for name, t in topics.items():
        if t["attempts"] > 0:
            pct = round(100 * t["correct"] / t["attempts"])
            print(f"{name}: {pct}% accuracy ({t['correct']}/{t['attempts']} correct)")
        else:
            print(f"{name}: not quizzed yet")

    print(f"\nTotal quiz sessions: {len(db['history'])}")


# ---------- ENTRY POINT ----------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "add" and len(sys.argv) > 2:
        cmd_add(sys.argv[2])
    elif command == "plan":
        cmd_plan()
    elif command == "quiz":
        cmd_quiz()
    elif command == "flashcards":
        cmd_flashcards()
    elif command == "progress":
        cmd_progress()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
