# IIUI Survey Bot

An automated Python script using Selenium to fill out university survey forms on the IIUI ERP portal.

## Features

- **Automated Login**: Securely logs in using credentials from a `.env` file.
- **Auto-Fill Surveys**: Automatically selects "Strongly Agree" (or custom rating) for radio button questions.
- **Auto-Comment**: Fills all text areas with a predefined comment.
- **Headless Mode Support**: Can run without a visible browser window (configurable).

## Prerequisites

- [Python 3.7+](https://www.python.org/downloads/)
- [Google Chrome](https://www.google.com/chrome/) installed.

## Installation

1.  **Clone or Download** this repository.
2.  **Install Dependencies**:
    ```bash
    pip install selenium python-dotenv webdriver-manager
    ```

## Configuration

1.  Create a file named `.env` in the project root directory.
2.  Add your IIUI ERP credentials:

    ```env
    IIUI_REG_NO=your_registration_number_here
    IIUI_PASSWORD=your_password_here
    ```

## Usage

1.  **Run the Bot**:
    ```bash
    python iiui_survey_bot.py
    ```
2.  **Follow the Prompts**:
    - The bot will log you in.
    - Manually navigate to the specific survey page you want to fill.
    - Press **ENTER** in the terminal to auto-fill the survey.
    - Review the filled survey and submit it manually.
    - Repeat for other surveys.

## Disclaimer

This tool is for educational purposes and personal automation only. Please ensure you comply with your university's IT policies when using automation tools.
