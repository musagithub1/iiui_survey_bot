# 🤖 IIUI Survey Bot

An automated Python bot that logs into the **IIUI ERP portal**, discovers every pending course and teacher evaluation, fills all answers automatically, and submits — without any manual clicks.

It comes with two ways to run it:
- **Streamlit Web UI** — enter your credentials in a browser form and watch live progress
- **Terminal CLI** — run directly from the command line

> ⚠️ **Disclaimer**: This tool is for educational purposes and personal automation only. Please ensure compliance with your university's IT and academic integrity policies before use.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔐 **Secure Credentials** | Entered via `.env` file or the Streamlit form — never hardcoded |
| 🔄 **Full Automation** | Logs in → scans survey table → fills every pending form → submits — all automatically |
| 🎯 **Smart Survey Discovery** | Reads the ERP table, skips already-submitted rows, queues all pending ones |
| ⭐ **Rating Selection** | Choose Strongly Agree → Strongly Disagree before starting |
| 💬 **Auto Comment** | Fills all textarea fields with a custom comment |
| 🖱️ **Handles All Field Types** | Radio buttons, text inputs, textareas, and `<select>` dropdowns |
| 🔁 **Retry Logic** | Retries login 3× and form fill 2× on any network or page-load failure |
| 📸 **Screenshot on Failure** | Saves a debug PNG to `./debug_screenshots/` whenever something goes wrong |
| 🌐 **Streamlit Web UI** | Premium dark-themed browser interface with live log streaming and result summary |
| 🕶️ **Headless Mode** | Run Chrome without a visible window (`IIUI_HEADLESS=true`) |
| ⏱️ **Configurable Timeout** | Set `IIUI_WAIT_TIMEOUT` for slow connections |

---

## 🧰 Prerequisites

1. **Python 3.10+** — [Download](https://www.python.org/downloads/)
2. **Google Chrome** — [Download](https://www.google.com/chrome/)
3. **Git** *(optional, for cloning)* — [Download](https://git-scm.com/downloads)

---

## 📥 Installation

### Step 1 — Get the project

**Clone with Git:**
```bash
git clone https://github.com/musagithub1/iiui_survey_bot.git
cd iiui_survey_bot
```

**Or download ZIP** from the GitHub page and extract it.

---

### Step 2 — Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> ✅ You'll see `(venv)` in your terminal when it's active. Run `deactivate` to exit later.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `selenium` — browser automation
- `webdriver-manager` — auto-downloads the correct ChromeDriver
- `python-dotenv` — loads `.env` credentials
- `streamlit` — web frontend

---

## ⚙️ Configuration

Create a `.env` file in the project root:

**macOS / Linux:**
```bash
nano .env
```

**Windows:** Create a new file named `.env` (not `.env.txt`) in the project folder using Notepad → Save As → All Files.

Paste your credentials:

```env
IIUI_REG_NO=your_registration_number
IIUI_PASSWORD=your_password

# Optional:
IIUI_HEADLESS=false        # true = hide browser window
IIUI_WAIT_TIMEOUT=20       # seconds to wait for pages (increase on slow connections)
```

> 🔒 The `.env` file is listed in `.gitignore` — it will never be uploaded to GitHub.

---

## ▶️ Usage

### Option A — Streamlit Web UI *(Recommended)*

```bash
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

**What you'll see:**

1. Enter your **Registration Number** and **Password** in the form
2. Select a **Rating** (Strongly Agree is default)
3. Optionally edit the **Comment** text
4. Click **🚀 Start Survey Bot**
5. Watch the live log stream as the bot works
6. A summary card shows how many surveys were completed, skipped, or failed

> 💡 No `.env` file needed when using the Streamlit UI — credentials are entered directly in the form.

---

### Option B — Command Line

```bash
# Windows
python iiui_survey_bot.py

# macOS / Linux
python3 iiui_survey_bot.py
```

**What happens:**

1. A rating menu appears — pick 1–5 or press Enter for Strongly Agree
2. Bot opens Chrome, logs in automatically
3. Navigates to the surveys page
4. Finds all pending surveys and fills + submits each one
5. Prints a summary when done

---

## 🔁 How the Automation Works

```
Login → /student/student-survey
           ↓
   Scan table for pending rows
   (skips "Response Submitted" badges)
           ↓
   For each pending survey:
     Open survey link
     Fill radios / textareas / selects
     Click Submit
     Handle confirm dialogs
     Go back → re-scan
           ↓
   Print summary
```

The bot loops until no more pending surveys are found (up to 20 passes safety cap).

---

## 📁 Project Structure

```
iiui_survey_bot/
├── app.py                 # Streamlit web frontend
├── iiui_survey_bot.py     # Core bot engine (CLI + importable class)
├── requirements.txt       # Python dependencies
├── .env                   # Your credentials (you create this — not in Git)
├── .gitignore             # Excludes .env, venv/, debug_screenshots/
├── debug_screenshots/     # Auto-created; failure PNGs saved here
└── README.md              # This file
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: python` | Use `python3` on macOS/Linux, or reinstall Python with "Add to PATH" checked |
| `ModuleNotFoundError` | Activate the venv first: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows), then `pip install -r requirements.txt` |
| Chrome doesn't open | Update Google Chrome — `webdriver-manager` auto-downloads the matching driver |
| Login fails | Check your `.env` for typos. A screenshot is saved to `./debug_screenshots/` |
| Survey fields not filled | Make sure a survey page is open; check `debug_screenshots/` for clues |
| Page times out | Set `IIUI_WAIT_TIMEOUT=40` in `.env` |
| "All surveys already submitted" | All evaluations for the current period are done — nothing to fill |
| Streamlit port in use | Run `streamlit run app.py --server.port 8502` to use a different port |

---

## 📄 License & Disclaimer

For **educational and personal automation** use only. Use responsibly and in accordance with IIUI's IT policies.
