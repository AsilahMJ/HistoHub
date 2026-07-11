"""
Study Agent — a TRUE AI agent that decides what to do next on its own.

The AI can see all your topics and progress, and has tools it can call:
  - get_progress        -> read your current stats
  - run_quiz            -> quiz you on a topic (AI picks which one)
  - show_flashcards     -> review flashcards for a topic
  - show_summary        -> re-read the summary for a topic
  - process_notes       -> process a new notes file into the system
  - update_score        -> save quiz results after a session

You just chat with it. It decides what to do.

Usage:
    python study_agent.py                        -> start the agent
    python study_agent.py add <notes_file.txt>   -> add notes, then chat
"""

import os
import sys
import json
import random
from datetime import datetime
from groq import Groq

# ─── SETUP ────────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("GROQ_API_KEY")
if not API_KEY:
    print("ERROR: Set your GROQ_API_KEY environment variable first.")
    print("  Mac/Linux:  export GROQ_API_KEY='your-key-here'")
    print("  Windows:    setx GROQ_API_KEY \"your-key-here\"  (then open a new terminal)")
    sys.exit(1)

client = Groq(api_key=API_KEY)
MODEL = "llama-3.3-70b-versatile"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "study_data.json")

# ─── DATA ─────────────────────────────────────────────────────────────────────

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {"topics": {}, "history": []}

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

# ─── TOOLS (functions the AI can call) ────────────────────────────────────────

# Tool schemas — this is what we send to Groq so it knows what tools exist
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_progress",
            "description": (
                "Returns all topics the student has studied, their quiz accuracy, "
                "attempts, and when they last studied each one. Use this to decide "
                "what to recommend next."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_quiz",
            "description": (
                "Runs an interactive quiz for a given topic. Returns the student's "
                "score. Call this when the student wants to be quizzed, or when you "
                "decide they need practice on a weak topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "Exact topic name as it appears in progress data.",
                    }
                },
                "required": ["topic_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_flashcards",
            "description": "Shows flashcards for a topic for the student to review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_name": {"type": "string", "description": "Exact topic name."}
                },
                "required": ["topic_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_summary",
            "description": "Shows the AI-generated summary for a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_name": {"type": "string", "description": "Exact topic name."}
                },
                "required": ["topic_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_notes",
            "description": (
                "Reads a notes file and processes it into a topic with summary, "
                "quiz questions, and flashcards. Use when the student provides a file path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the .txt notes file.",
                    }
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_score",
            "description": "Saves a quiz result to the student's progress record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_name": {"type": "string"},
                    "correct": {"type": "integer"},
                    "total": {"type": "integer"},
                },
                "required": ["topic_name", "correct", "total"],
            },
        },
    },
]

# ─── TOOL IMPLEMENTATIONS ──────────────────────────────────────────────────────

def tool_get_progress():
    db = load_db()
    topics = db["topics"]
    if not topics:
        return {"status": "no_topics", "message": "No topics added yet."}
    result = []
    for name, t in topics.items():
        accuracy = round(t["correct"] / t["attempts"], 2) if t["attempts"] > 0 else None
        result.append({
            "topic": name,
            "accuracy": accuracy,
            "attempts": t["attempts"],
            "correct": t["correct"],
            "last_studied": t.get("last_studied", "never"),
        })
    return {"topics": result, "total_sessions": len(db["history"])}


def tool_run_quiz(topic_name):
    db = load_db()
    topic = db["topics"].get(topic_name)
    if not topic:
        return {"error": f"Topic '{topic_name}' not found."}

    questions = list(topic["quiz"])
    random.shuffle(questions)
    correct_count = 0

    print(f"\n{'='*50}")
    print(f"  QUIZ: {topic_name}")
    print(f"{'='*50}\n")

    for q in questions:
        print(q["question"])
        for i, opt in enumerate(q["options"]):
            print(f"  {chr(97+i)}) {opt}")

        raw_answer = q["answer"].strip()
        correct_index = None
        if len(raw_answer) == 1 and raw_answer.lower() in "abcd":
            correct_index = "abcd".index(raw_answer.lower())
        else:
            for i, opt in enumerate(q["options"]):
                if opt.strip().lower() == raw_answer.lower():
                    correct_index = i
                    break
        if correct_index is None:
            correct_index = 0

        correct_letter = chr(97 + correct_index)
        ans = input("Your answer (a/b/c/d): ").strip().lower()

        if ans == correct_letter:
            print("✓ Correct!\n")
            correct_count += 1
        else:
            print(f"✗ Incorrect. Answer: {correct_letter}) {q['options'][correct_index]}\n")

    total = len(questions)
    pct = round(100 * correct_count / total)
    print(f"Quiz complete! Score: {correct_count}/{total} ({pct}%)\n")

    # Save immediately
    topic["attempts"] += total
    topic["correct"] += correct_count
    topic["last_studied"] = datetime.now().isoformat()
    db["history"].append({
        "date": datetime.now().isoformat(),
        "topic": topic_name,
        "score": f"{correct_count}/{total}",
    })
    save_db(db)

    return {"topic": topic_name, "correct": correct_count, "total": total, "percent": pct}


def tool_show_flashcards(topic_name):
    db = load_db()
    topic = db["topics"].get(topic_name)
    if not topic:
        return {"error": f"Topic '{topic_name}' not found."}

    cards = list(topic["flashcards"])
    random.shuffle(cards)

    print(f"\n{'='*50}")
    print(f"  FLASHCARDS: {topic_name}")
    print(f"  {len(cards)} cards — press Enter to flip each one")
    print(f"{'='*50}\n")

    for i, card in enumerate(cards, 1):
        input(f"[{i}/{len(cards)}] {card['front']}\n  → Press Enter to reveal...")
        print(f"  {card['back']}\n")

    return {"status": "complete", "cards_reviewed": len(cards)}


def tool_show_summary(topic_name):
    db = load_db()
    topic = db["topics"].get(topic_name)
    if not topic:
        return {"error": f"Topic '{topic_name}' not found."}

    print(f"\n{'='*50}")
    print(f"  SUMMARY: {topic_name}")
    print(f"{'='*50}\n")
    print(topic["summary"])
    print()

    return {"status": "shown", "topic": topic_name}


def tool_process_notes(filepath):
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    with open(filepath, "r") as f:
        notes_text = f.read()

    print(f"\nProcessing notes from {filepath}...")

    system = (
        "You are a study assistant. Given lecture notes, extract a single main "
        "topic name (2-4 words), a clear summary (150-250 words), 5 quiz questions "
        "(multiple choice, 4 options each), and 8 flashcards (front/back). "
        "The 'answer' field MUST be a single lowercase letter (a, b, c, or d). "
        "Respond ONLY in valid JSON: "
        '{"topic": "...", "summary": "...", '
        '"quiz": [{"question": "...", "options": ["..","..","..",".."], "answer": "a"}], '
        '"flashcards": [{"front": "...", "back": "..."}]}'
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": notes_text}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    result = json.loads(response.choices[0].message.content)

    db = load_db()
    topic_name = result["topic"]
    existing = db["topics"].get(topic_name, {})
    db["topics"][topic_name] = {
        "summary": result["summary"],
        "quiz": result["quiz"],
        "flashcards": result["flashcards"],
        "attempts": existing.get("attempts", 0),
        "correct": existing.get("correct", 0),
        "last_studied": existing.get("last_studied", datetime.now().isoformat()),
        "added": datetime.now().isoformat(),
    }
    save_db(db)

    print(f"✓ Added topic: {topic_name}\n")
    return {
        "status": "success",
        "topic": topic_name,
        "quiz_questions": len(result["quiz"]),
        "flashcards": len(result["flashcards"]),
        "summary_preview": result["summary"][:120] + "...",
    }


def tool_update_score(topic_name, correct, total):
    db = load_db()
    topic = db["topics"].get(topic_name)
    if not topic:
        return {"error": f"Topic '{topic_name}' not found."}
    topic["attempts"] += total
    topic["correct"] += correct
    topic["last_studied"] = datetime.now().isoformat()
    save_db(db)
    return {"status": "saved", "topic": topic_name}


# Map tool names to actual functions
TOOL_REGISTRY = {
    "get_progress": lambda args: tool_get_progress(),
    "run_quiz": lambda args: tool_run_quiz(args["topic_name"]),
    "show_flashcards": lambda args: tool_show_flashcards(args["topic_name"]),
    "show_summary": lambda args: tool_show_summary(args["topic_name"]),
    "process_notes": lambda args: tool_process_notes(args["filepath"]),
    "update_score": lambda args: tool_update_score(
        args["topic_name"], args["correct"], args["total"]
    ),
}

# ─── AGENT LOOP ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a proactive, encouraging study agent. You have access to
tools that let you see the student's progress, run quizzes, show flashcards, show
summaries, and process new notes.

Your job is NOT to wait for the student to tell you what to do. Instead:
1. At the start of each conversation, call get_progress to see where they stand.
2. Based on what you see, proactively suggest or immediately start the most helpful
   activity — quiz a weak topic, review flashcards for something not studied recently,
   or celebrate improvement.
3. After a quiz, reflect on the score and decide whether to drill more, show the
   summary to reinforce weak areas, or move on to the next topic.
4. Keep responses concise and warm. You are a coach, not just a chatbot.
5. If the student mentions a file path (e.g. "add biology.txt"), call process_notes.
6. Always think: "What does this student need RIGHT NOW to make progress?" Then do it."""


def run_agent():
    """The main agent loop — the AI drives, not the user."""
    db = load_db()
    topic_count = len(db["topics"])

    print("\n" + "="*50)
    print("  STUDY AGENT")
    print("="*50)
    if topic_count == 0:
        print("No topics yet. Tell me a file to add, e.g.:")
        print("  You: add data/sample_notes.txt\n")
    else:
        print(f"  {topic_count} topic(s) loaded. Checking your progress...\n")

    # Conversation history — this is the memory the agent uses
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Kick off the agent with an opening message
    opening = (
        "Hello! I'm checking your progress now."
        if topic_count > 0
        else "Hello! I'm your study agent. Share a notes file to get started."
    )
    messages.append({"role": "user", "content": opening})

    while True:
        # ── Ask the AI what to do next ──────────────────────────────────────
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.5,
        )

        msg = response.choices[0].message

        # ── Handle tool calls the AI decided to make ─────────────────────────
        if msg.tool_calls:
            # Add the assistant's decision to history
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each tool and feed results back
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)

                print(f"[agent is calling: {tool_name}]")

                try:
                    result = TOOL_REGISTRY[tool_name](tool_args)
                except Exception as e:
                    result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

            # Let the AI continue reasoning after seeing tool results
            continue

        # ── No tool calls — AI is talking to the user ─────────────────────────
        agent_reply = msg.content or ""
        if agent_reply:
            print(f"\nAgent: {agent_reply}\n")

        messages.append({"role": "assistant", "content": agent_reply})

        # ── Get user input ────────────────────────────────────────────────────
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! Keep studying. 👋")
            break

        if user_input.lower() in ("exit", "quit", "bye", "q"):
            print("\nGoodbye! Keep studying. 👋")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    # If called with "add <file>", pre-load the notes then start the agent
    if len(sys.argv) == 3 and sys.argv[1] == "add":
        filepath = sys.argv[2]
        print(f"\nPre-loading notes from: {filepath}")
        result = tool_process_notes(filepath)
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)

    run_agent()


if __name__ == "__main__":
    main()
