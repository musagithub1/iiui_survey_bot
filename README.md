# 🤖 IIUI Survey Bot

An automated Python script that uses Selenium to fill out university survey forms on the **IIUI ERP portal** — saving you time on repetitive course evaluations.

> ⚠️ **Disclaimer**: This tool is for educational purposes and personal automation only. Please make sure you comply with your university's IT policies before using automation tools.

---

## ✨ Features

- 🔐 **Automated Login** — securely logs in using credentials stored in a `.env` file (never hardcoded).
- ✅ **Login Verification** — confirms the dashboard actually loaded after login; detects and reports error messages from the portal.
- ⭐ **Interactive Rating Selection** — choose your preferred rating (Strongly Agree → Strongly Disagree) from a menu at startup.
- 🎯 **Auto-Fill Surveys** — fills radio buttons, text inputs, textareas, **and `<select>` dropdowns** in one pass.
- 🔄 **Automatic Retry** — retries login up to 3× and fill up to 2× on network or page-load failures.
- 📸 **Screenshot on Failure** — saves a PNG to `./debug_screenshots/` whenever something goes wrong, so you can diagnose issues instantly.
- 🚗 **Auto-Navigate to Surveys** — after login, automatically opens the surveys listing page.
- 🕶️ **Headless Mode** — run with or without a visible browser via the `IIUI_HEADLESS` env var.
- ⏱️ **Configurable Timeout** — set `IIUI_WAIT_TIMEOUT` in your `.env` to adjust for slow connections.
- 🛡️ **Robust Selectors** — tries multiple CSS/XPath fallbacks for login fields so a minor ERP page update won't break the bot.

---

## 🧰 Prerequisites

Before you start, make sure you have:

1. **Python 3.10 or newer** — [Download Python](https://www.python.org/downloads/)
2. **Google Chrome** — [Download Chrome](https://www.google.com/chrome/)
3. **Git** (optional, only needed if cloning the repo) — [Download Git](https://git-scm.com/downloads)

### ✅ Checking if Python is installed

**Windows:**
```bash
python --version
```

**macOS / Linux:**
```bash
python3 --version
```

If you see a version number (e.g., `Python 3.11.4`), you're good to go. If not, install Python using the link above — and on Windows, make sure to check the box **"Add Python to PATH"** during installation.

---

## 📥 Installation

### Step 1: Get the project

**Option A — Clone with Git:**
```bash
git clone https://github.com/musagithub1/iiui_survey_bot.git
cd iiui_survey_bot
```

**Option B — Download manually:**
1. Click the green **"Code"** button on the GitHub repo page.
2. Select **"Download ZIP"**.
3. Extract the ZIP file to a folder of your choice.
4. Open a terminal/command prompt in that folder.

### Step 2: Create a virtual environment (recommended)

A virtual environment keeps this project's dependencies separate from your system Python, avoiding version conflicts with other projects.

**Create the virtual environment:**

**Windows:**
```bash
python -m venv venv
```

**macOS / Linux:**
```bash
python3 -m venv venv
```

**Activate the virtual environment:**

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

> ✅ Once activated, you'll see `(venv)` at the start of your terminal line. This means everything you install next will stay isolated to this project.
>
> 💡 To exit the virtual environment later, simply type `deactivate`.

### Step 3: Install dependencies

With your virtual environment activated, run:

```bash
pip install -r requirements.txt
```

> 💡 **Note**: Inside an activated virtual environment, `pip` automatically points to the correct Python version — no need for `pip3` or `--user`.

---

## ⚙️ Configuration

You need to tell the bot your IIUI ERP login details. **These are stored locally and never shared.**

### Step 1: Create a `.env` file

In the project's root folder, create a new file named exactly:
```
.env
```

**Windows users:** Note that Windows File Explorer may not let you create a file starting with a dot through the normal "New File" menu. Instead:
1. Open **Notepad**.
2. Type your credentials (see below).
3. Click **File > Save As**.
4. In the "Save as type" dropdown, choose **"All Files"**.
5. Name the file `.env` (including the dot) and save it inside the project folder.

**macOS / Linux users:** You can create it directly from the terminal:
```bash
nano .env
```

### Step 2: Add your credentials

Paste the following into the `.env` file, replacing the placeholders with your real details:

```env
IIUI_REG_NO=your_registration_number_here
IIUI_PASSWORD=your_password_here

# Optional settings:
IIUI_HEADLESS=false          # Set to true to hide the browser window
IIUI_WAIT_TIMEOUT=20         # Seconds to wait for pages to load (increase on slow connections)
```

Save and close the file.

> 🔒 **Security note**: Never share your `.env` file or commit it to GitHub. If using Git, make sure `.env` is listed in your `.gitignore` file.

---

## ▶️ Usage

> 💡 If you closed your terminal since installation, make sure to **activate the virtual environment again** before running the bot (see Installation Step 2). You should see `(venv)` in your terminal.

### Step 1: Run the bot

**Windows:**
```bash
python iiui_survey_bot.py
```

**macOS / Linux:**
```bash
python3 iiui_survey_bot.py
```

### Step 2: Select your rating

At startup, the bot will display a menu:

```
═══════════════════════════════════════════════════════
  SELECT DEFAULT RATING FOR ALL RADIO QUESTIONS
═══════════════════════════════════════════════════════
  1. Strongly Agree
  2. Agree
  3. Neutral
  4. Disagree
  5. Strongly Disagree
  (Press ENTER to keep default: Strongly Agree)
═══════════════════════════════════════════════════════
```

Type a number (1–5) and press ENTER, or just press ENTER to use "Strongly Agree".

### Step 3: Follow the on-screen prompts

1. The bot will open Chrome and **automatically log in** to the ERP portal.
2. The bot will **automatically navigate** to the surveys listing page.
3. **Click on a specific survey** in the browser to open it.
4. Switch back to the terminal and press **ENTER** — this triggers the auto-fill.
5. **Review** the filled-in answers and comments on the survey page.
6. **Submit the survey manually** (the bot does not click submit for you, by design).
7. Repeat steps 3–6 for any additional surveys.

---

## 🛠️ Troubleshooting

| Problem | Possible Fix |
|---|---|
| `command not found: python` | Use `python3` instead of `python` (common on macOS/Linux), or reinstall Python and check "Add to PATH". |
| `cannot be loaded because running scripts is disabled` (PowerShell) | Run PowerShell as Administrator and execute: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`, then try activating the venv again. |
| `ModuleNotFoundError` | Make sure your virtual environment is activated (you should see `(venv)`), then re-run `pip install -r requirements.txt`. |
| Chrome doesn't open / version mismatch error | Make sure Google Chrome is up to date — `webdriver-manager` will auto-download the matching driver. |
| Login fails | Double-check your `.env` file for typos and make sure there are no extra spaces around the `=` sign. A screenshot will be saved to `./debug_screenshots/` to help diagnose the issue. |
| `.env` file not found | Make sure the file is named exactly `.env` (not `.env.txt`) and is in the same folder as the script. |
| Survey fields not filled | Make sure you have opened a **specific survey page** (not just the listing) before pressing ENTER in the terminal. |
| Page times out | Increase `IIUI_WAIT_TIMEOUT` in your `.env` (e.g., `IIUI_WAIT_TIMEOUT=40`). |

---

## 📁 Project Structure

```
iiui_survey_bot/
├── venv/                  # Virtual environment (created by you, not in Git)
├── debug_screenshots/     # Auto-created; failure screenshots saved here
├── iiui_survey_bot.py     # Main script
├── requirements.txt       # Python dependencies
├── .env                   # Your credentials (you create this)
├── .gitignore             # Excludes venv/ and .env from Git
└── README.md              # This file
```

> 🔒 **Important**: Add a `.gitignore` file with the following lines so you never accidentally upload your credentials or virtual environment:
> ```
> venv/
> .env
> debug_screenshots/
> ```

---

## 📄 License & Disclaimer

This project is intended for **educational purposes and personal automation only**. Use responsibly and ensure compliance with your university's IT and academic integrity policies.
