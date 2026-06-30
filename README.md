# Study Agent

Turns your lecture notes into summaries, quizzes, and flashcards — and
tracks your progress over time so it knows what to focus on next.

## What you need

- A free [GitHub](https://github.com) account
- A free [Groq](https://console.groq.com) account (for the API key)
- [VS Code](https://code.visualstudio.com) installed
- [Python 3.10+](https://www.python.org/downloads/) installed

## Setup (do this once)

### 1. Get your free Groq API key
1. Go to https://console.groq.com and sign up (free, no credit card).
2. Click **API Keys** in the left sidebar.
3. Click **Create API Key**, name it anything, and copy the key.
   You will only see it once — paste it somewhere safe temporarily.

### 2. Create your GitHub repository
1. Go to https://github.com and sign in.
2. Click the **+** in the top right → **New repository**.
3. Name it `study-agent`, keep it **Public** or **Private** (your choice),
   check **Add a README file**, then click **Create repository**.

### 3. Clone it into VS Code
1. Open VS Code.
2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac), type
   **Git: Clone**, and press Enter.
3. Paste your repo URL (copy it from the green **Code** button on GitHub).
4. Choose a folder on your computer to save it, then open it when prompted.

### 4. Add the project files
1. Copy `study_agent.py` and `requirements.txt` into your cloned folder.
2. Create a folder inside it called `data` (this stores your progress —
   it's created automatically the first time you run the script too).

### 5. Install Python dependencies
Open the VS Code terminal (`` Ctrl+` `` or `` Cmd+` ``) and run:

```bash
pip install -r requirements.txt
```

### 6. Set your API key as an environment variable

**Do not paste your API key directly into the code** — anyone who sees
your code (e.g. on GitHub) could steal it and rack up usage on your account.

Mac/Linux (in the VS Code terminal):
```bash
export GROQ_API_KEY="paste-your-key-here"
```

Windows (in PowerShell):
```powershell
$env:GROQ_API_KEY="paste-your-key-here"
```

This only lasts for your current terminal session. To make it permanent,
add the same line to your shell profile (`.zshrc`, `.bashrc`) on Mac/Linux,
or use `setx GROQ_API_KEY "your-key"` on Windows (then restart the terminal).

### 7. Protect your API key on GitHub
Create a file called `.gitignore` in your project folder with this line:
```
data/
.env
```
This stops your personal study data and any secrets file from being
uploaded to GitHub. Never commit your API key itself.

## How to use it

```bash
# Add your lecture notes (paste your real notes into a .txt file first)
python study_agent.py add data/sample_notes.txt

# See your AI-generated, prioritized study plan
python study_agent.py plan

# Take a quiz on your weakest topic
python study_agent.py quiz

# Review flashcards
python study_agent.py flashcards

# Check your progress over time
python study_agent.py progress
```

## How the "updates with learning progress" part works

Every time you take a quiz, your score for that topic is saved in
`data/study_data.json`. When you run `plan`, the AI looks at your
accuracy per topic and how recently you studied each one, and
re-prioritizes what to focus on next. The more you quiz yourself,
the smarter the plan gets.

## Save your progress to GitHub

After adding notes or taking quizzes, save your code changes (not your
personal data, thanks to `.gitignore`) with:

```bash
git add .
git commit -m "Updated study agent"
git push
```

## Extending it (optional next steps)

- Add a real text file of your own lecture notes instead of the sample
- Swap `llama-3.3-70b-versatile` for a different free Groq model if you want
- Add a daily reminder using `ntfy.sh` (free push notifications)
- Build a simple web interface later using Streamlit (also free)
