"""
IIUI Survey Bot — Robust Edition
Automates IIUI ERP survey filling using Selenium.

Usage:
    python iiui_survey_bot.py

Configuration (via .env or environment variables):
    IIUI_REG_NO      — Your IIUI registration number
    IIUI_PASSWORD    — Your ERP portal password
    IIUI_HEADLESS    — Set to "true" to run without a visible browser (default: false)
    IIUI_WAIT_TIMEOUT — Page wait timeout in seconds (default: 20)
"""

import os
import sys
import time
import logging
import functools
import traceback
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementNotInteractableException,
)

# ── Optional dependency: python-dotenv ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env loading is optional; env vars may already be set

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def retry(max_attempts: int = 3, delay: float = 2.0, exceptions=(Exception,)):
    """Decorator — retries a method up to *max_attempts* times on failure."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        logger.warning(
                            f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: {exc}. "
                            f"Retrying in {delay}s…"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[{func.__name__}] All {max_attempts} attempts failed."
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# ── Rating choices ─────────────────────────────────────────────────────────────
RATING_OPTIONS = [
    "Strongly Agree",
    "Agree",
    "Neutral",
    "Disagree",
    "Strongly Disagree",
]


def prompt_rating() -> str:
    """Interactively ask the user which rating to apply."""
    print("\n" + "═" * 55)
    print("  SELECT DEFAULT RATING FOR ALL RADIO QUESTIONS")
    print("═" * 55)
    for i, opt in enumerate(RATING_OPTIONS, 1):
        print(f"  {i}. {opt}")
    print("  (Press ENTER to keep default: Strongly Agree)")
    print("═" * 55)
    while True:
        choice = input("  Your choice [1-5]: ").strip()
        if choice == "":
            return RATING_OPTIONS[0]
        if choice.isdigit() and 1 <= int(choice) <= len(RATING_OPTIONS):
            return RATING_OPTIONS[int(choice) - 1]
        print("  ⚠  Invalid input. Please enter a number between 1 and 5.")


# ── Main Bot Class ─────────────────────────────────────────────────────────────

class IIUISurveyBot:
    """
    Selenium-based bot for filling IIUI ERP surveys.

    Key robustness features:
    - Safe driver init: self.driver starts as None; close() is always safe.
    - Multi-selector login fallbacks.
    - Login verification via URL change + dashboard element detection.
    - Retry decorator on network-bound methods.
    - Screenshot-on-failure saved to ./debug_screenshots/.
    - Configurable timeout via IIUI_WAIT_TIMEOUT env var.
    - Handles radio buttons, text inputs, textareas, and <select> dropdowns.
    """

    BASE_URL = "https://erp.iiui.edu.pk/student/login"
    DASHBOARD_URL_FRAGMENT = "/student/dashboard"
    SURVEYS_URL = "https://erp.iiui.edu.pk/student/survey"

    # Candidate selectors tried in order for the registration field
    _REG_SELECTORS = [
        (By.ID, "email"),
        (By.NAME, "email"),
        (By.NAME, "username"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[placeholder*='egistration']"),
        (By.CSS_SELECTOR, "input[placeholder*='mail']"),
    ]
    # Candidate selectors for the password field
    _PASS_SELECTORS = [
        (By.ID, "password"),
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]
    # Candidate selectors for the submit button
    _SUBMIT_SELECTORS = [
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]"),
        (By.XPATH, "//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]"),
    ]
    # CSS patterns that indicate a login error message on the page
    _ERROR_SELECTORS = [
        (By.CSS_SELECTOR, ".alert-danger"),
        (By.CSS_SELECTOR, ".error"),
        (By.CSS_SELECTOR, "[class*='error']"),
        (By.CSS_SELECTOR, ".invalid-feedback"),
    ]

    def __init__(
        self,
        registration_no: str | None = None,
        password: str | None = None,
        headless: bool | None = None,
        timeout: int | None = None,
    ):
        self.driver = None  # Always initialise to None so close() is safe

        self.registration_no = registration_no or os.getenv("IIUI_REG_NO", "")
        self.password = password or os.getenv("IIUI_PASSWORD", "")

        # Headless: explicit arg > env var > default False
        if headless is None:
            headless = os.getenv("IIUI_HEADLESS", "false").lower() == "true"

        # Timeout: explicit arg > env var > default 20 s
        if timeout is None:
            timeout = int(os.getenv("IIUI_WAIT_TIMEOUT", "20"))
        self.timeout = timeout

        # Screenshot directory
        self._screenshot_dir = Path("debug_screenshots")
        self._screenshot_dir.mkdir(exist_ok=True)

        # Build Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,900")
        chrome_options.add_argument("--log-level=3")  # Suppress Chrome noise
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Initialise ChromeDriver
        try:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                logger.info("Setting up ChromeDriver via webdriver-manager…")
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options,
                )
            except ImportError:
                logger.warning(
                    "webdriver-manager not installed — using system ChromeDriver. "
                    "Install it with: pip install webdriver-manager"
                )
                self.driver = webdriver.Chrome(options=chrome_options)

            self.wait = WebDriverWait(self.driver, self.timeout)
            logger.info(f"Browser ready. (timeout={self.timeout}s, headless={headless})")

        except WebDriverException as exc:
            logger.error(f"Failed to launch ChromeDriver: {exc}")
            logger.error(
                "Make sure Google Chrome is installed and up-to-date, "
                "or install webdriver-manager: pip install webdriver-manager"
            )
            raise  # Re-raise so the caller can handle it cleanly

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _screenshot(self, label: str) -> str | None:
        """Save a screenshot and return its path, or None on failure."""
        if self.driver is None:
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self._screenshot_dir / f"{ts}_{label}.png"
        try:
            self.driver.save_screenshot(str(path))
            logger.info(f"📸 Screenshot saved: {path}")
            return str(path)
        except Exception:
            return None

    def _find_first(self, selectors: list[tuple], timeout: float = 5) -> object | None:
        """Try each (By, value) selector in order; return the first visible element found."""
        for by, value in selectors:
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, value))
                )
                return el
            except (TimeoutException, NoSuchElementException):
                continue
        return None

    def _detect_login_error(self) -> str | None:
        """Return the text of an on-page login error message, or None."""
        for by, selector in self._ERROR_SELECTORS:
            try:
                els = self.driver.find_elements(by, selector)
                for el in els:
                    text = el.text.strip()
                    if text:
                        return text
            except Exception:
                continue
        return None

    # ── Public API ──────────────────────────────────────────────────────────────

    @retry(max_attempts=3, delay=3.0, exceptions=(WebDriverException, TimeoutException))
    def login(self) -> bool:
        """
        Log in to the IIUI ERP portal.

        Returns:
            True  — login succeeded (dashboard URL detected).
            False — login failed (bad credentials, network error, etc.).
        """
        if not self.registration_no or not self.password:
            logger.error(
                "Credentials missing! Set IIUI_REG_NO and IIUI_PASSWORD in your .env file."
            )
            return False

        logger.info(f"Navigating to login page: {self.BASE_URL}")
        self.driver.get(self.BASE_URL)

        # ── Registration field ──────────────────────────────────────────────
        reg_field = self._find_first(self._REG_SELECTORS, timeout=self.timeout)
        if reg_field is None:
            self._screenshot("no_reg_field")
            logger.error(
                "Could not find the registration/email input field. "
                "The ERP page layout may have changed."
            )
            return False

        reg_field.clear()
        reg_field.send_keys(self.registration_no)
        logger.debug(f"Entered registration number into: {reg_field.get_attribute('outerHTML')[:120]}")

        # ── Password field ──────────────────────────────────────────────────
        pass_field = self._find_first(self._PASS_SELECTORS, timeout=5)
        if pass_field is None:
            self._screenshot("no_pass_field")
            logger.error("Could not find the password input field.")
            return False

        pass_field.clear()
        pass_field.send_keys(self.password)

        # ── Submit button ───────────────────────────────────────────────────
        submit_btn = self._find_first(self._SUBMIT_SELECTORS, timeout=5)
        if submit_btn is None:
            self._screenshot("no_submit_btn")
            logger.error("Could not find the login/submit button.")
            return False

        submit_btn.click()
        logger.info("Login form submitted. Waiting for response…")

        # ── Verify login success ────────────────────────────────────────────
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: self.DASHBOARD_URL_FRAGMENT in d.current_url
                or d.current_url != self.BASE_URL
            )
        except TimeoutException:
            pass  # Check for error message below

        current_url = self.driver.current_url
        logger.debug(f"URL after submit: {current_url}")

        if self.DASHBOARD_URL_FRAGMENT in current_url:
            logger.info("✅ Login successful! Dashboard loaded.")
            return True

        # Check for an explicit error message on the page
        error_text = self._detect_login_error()
        if error_text:
            self._screenshot("login_error")
            logger.error(f"❌ Login failed — Portal says: \"{error_text}\"")
            return False

        # Still on the login page with no obvious error → likely wrong credentials
        if "login" in current_url.lower():
            self._screenshot("login_stuck")
            logger.error(
                "❌ Login failed — still on login page after submit. "
                "Check your registration number and password."
            )
            return False

        # URL changed but not to dashboard (could be 2FA, survey prompt, etc.)
        logger.warning(
            f"⚠ Login redirected to an unexpected URL: {current_url}. "
            "The bot will continue, but behaviour may be unpredictable."
        )
        return True

    @retry(max_attempts=2, delay=2.0, exceptions=(WebDriverException,))
    def navigate_to_surveys(self) -> bool:
        """
        Navigate to the surveys listing page.

        Returns:
            True if the page loaded successfully, False otherwise.
        """
        logger.info(f"Navigating to surveys page: {self.SURVEYS_URL}")
        try:
            self.driver.get(self.SURVEYS_URL)
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.info("Surveys page loaded.")
            return True
        except TimeoutException:
            self._screenshot("surveys_page_timeout")
            logger.error("Surveys page did not fully load within the timeout.")
            return False
        except WebDriverException as exc:
            self._screenshot("surveys_nav_error")
            logger.error(f"Error navigating to surveys page: {exc}")
            return False

    @retry(max_attempts=2, delay=1.5, exceptions=(WebDriverException,))
    def fill_survey(
        self,
        rating_choice: str = "Strongly Agree",
        comment_text: str = "I filled this survey using my personal Agent, Thank you",
    ) -> dict:
        """
        Fill all form fields on the currently active survey page.

        Args:
            rating_choice: Text that should match the desired radio label
                           (e.g. "Strongly Agree", "Agree", "Neutral").
            comment_text:  Text to place in all visible text inputs / textareas.

        Returns:
            A dict with counts: {"radios": N, "texts": M, "selects": K, "success": bool}
        """
        result = {"radios": 0, "texts": 0, "selects": 0, "success": False}

        try:
            logger.info(f"Filling survey — rating: \"{rating_choice}\"")

            # Wait for at least one form element to appear
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input, textarea, select"))
                )
            except TimeoutException:
                self._screenshot("no_form_elements")
                logger.error(
                    "No form elements found on the page. "
                    "Make sure you have navigated to a survey page."
                )
                return result

            # ── 1. Radio Buttons ──────────────────────────────────────────────
            radios_filled = self.driver.execute_script(
                """
                const ratingChoice = arguments[0].toLowerCase().trim();
                const radios = document.querySelectorAll('input[type="radio"]');
                const groups = {};

                radios.forEach(radio => {
                    const name = radio.name;
                    if (name) {
                        if (!groups[name]) groups[name] = [];
                        groups[name].push(radio);
                    }
                });

                let filled = 0;
                Object.values(groups).forEach(options => {
                    let clicked = false;

                    for (const opt of options) {
                        // Try label[for="id"], sibling label, or parent label
                        const byFor = opt.id
                            ? document.querySelector('label[for="' + opt.id + '"]')
                            : null;
                        const sibling = opt.nextElementSibling &&
                            opt.nextElementSibling.tagName === 'LABEL'
                            ? opt.nextElementSibling : null;
                        const parent = opt.closest('label');
                        const label = byFor || sibling || parent;

                        const labelText = label ? label.innerText.toLowerCase().trim() : '';
                        const optValue = opt.value ? opt.value.toLowerCase().trim() : '';

                        if (labelText.includes(ratingChoice) || optValue.includes(ratingChoice)) {
                            opt.checked = true;
                            opt.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                            opt.dispatchEvent(new Event('input', { bubbles: true }));
                            opt.dispatchEvent(new Event('change', { bubbles: true }));
                            clicked = true;
                            filled++;
                            break;
                        }
                    }

                    // Fallback: if exact label not found, click the first option
                    if (!clicked && options.length > 0) {
                        options[0].checked = true;
                        options[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
                        options[0].dispatchEvent(new Event('input', { bubbles: true }));
                        options[0].dispatchEvent(new Event('change', { bubbles: true }));
                        filled++;
                    }
                });

                return filled;
                """,
                rating_choice,
            )
            result["radios"] = radios_filled or 0
            logger.info(f"  ✔ Radio groups filled: {result['radios']}")

            # ── 2. Text Inputs & Textareas ────────────────────────────────────
            texts_filled = self.driver.execute_script(
                """
                const commentText = arguments[0];
                const skipIds = ['search-friends', 'search', 'q'];
                const textEls = document.querySelectorAll(
                    'textarea, input[type="text"], input[type="search"]'
                );
                let count = 0;

                textEls.forEach(el => {
                    // Skip hidden / search fields
                    if (skipIds.includes(el.id)) return;
                    if (el.offsetWidth === 0 && el.offsetHeight === 0) return;
                    if (el.readOnly || el.disabled) return;

                    // Use native value setter so React/Vue state syncs
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        el.tagName === 'TEXTAREA'
                            ? HTMLTextAreaElement.prototype
                            : HTMLInputElement.prototype,
                        'value'
                    );
                    if (nativeSetter && nativeSetter.set) {
                        nativeSetter.set.call(el, commentText);
                    } else {
                        el.value = commentText;
                    }

                    el.dispatchEvent(new Event('input',  { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur',   { bubbles: true }));
                    count++;
                });

                return count;
                """,
                comment_text,
            )
            result["texts"] = texts_filled or 0
            logger.info(f"  ✔ Text/textarea fields filled: {result['texts']}")

            # ── 3. Select Dropdowns ───────────────────────────────────────────
            selects_filled = self.driver.execute_script(
                """
                const ratingChoice = arguments[0].toLowerCase().trim();
                const selects = document.querySelectorAll('select');
                let count = 0;

                selects.forEach(sel => {
                    if (sel.disabled || sel.offsetWidth === 0) return;

                    let matched = false;
                    for (const opt of sel.options) {
                        if (opt.text.toLowerCase().trim().includes(ratingChoice)) {
                            sel.value = opt.value;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            matched = true;
                            count++;
                            break;
                        }
                    }
                    // Fallback: pick first non-empty option
                    if (!matched && sel.options.length > 1) {
                        sel.value = sel.options[1].value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        count++;
                    }
                });

                return count;
                """,
                rating_choice,
            )
            result["selects"] = selects_filled or 0
            logger.info(f"  ✔ Select dropdowns filled: {result['selects']}")

            total = result["radios"] + result["texts"] + result["selects"]
            if total == 0:
                self._screenshot("nothing_filled")
                logger.warning(
                    "⚠ No fields were filled. The page may not contain a survey form yet. "
                    "Make sure you have opened a specific survey before pressing ENTER."
                )
            else:
                logger.info(f"🎉 Survey filled! Total fields: {total}")
                result["success"] = True

            return result

        except Exception as exc:
            self._screenshot("fill_error")
            logger.error(f"Unexpected error during fill_survey: {exc}")
            logger.debug(traceback.format_exc())
            return result

    def close(self):
        """Quit the browser. Safe to call even if the driver never started."""
        if self.driver is not None:
            try:
                self.driver.quit()
                logger.info("Browser closed.")
            except Exception:
                pass  # Already dead
            self.driver = None


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print("═" * 55)
    print("       IIUI SURVEY BOT — Robust Edition")
    print("═" * 55)

    # Interactive rating selection
    rating = prompt_rating()
    comment = (
        "I filled this survey using my personal Agent, Thank you"
    )
    print(f"\n  Rating : {rating}")
    print(f"  Comment: {comment}\n")

    headless = os.getenv("IIUI_HEADLESS", "false").lower() == "true"

    try:
        bot = IIUISurveyBot(headless=headless)
    except WebDriverException:
        print("\n[FATAL] Could not start Chrome. See error above. Exiting.")
        sys.exit(1)

    try:
        if not bot.login():
            print("\n[FATAL] Login failed. Check your credentials in .env and try again.")
            sys.exit(1)

        # Auto-navigate to surveys listing
        bot.navigate_to_surveys()

        print("\n" + "═" * 55)
        print("  LOGIN SUCCESSFUL")
        print("  The surveys page has been loaded for you.")
        print("  Steps:")
        print("    1. Click on a specific survey in the browser.")
        print("    2. Wait for the survey questions to load.")
        print("    3. Come back here and press ENTER to auto-fill.")
        print("    4. Review answers, then manually click 'Submit'.")
        print("    5. Repeat for each additional survey.")
        print("  Type 'q' to quit at any time.")
        print("═" * 55)

        while True:
            try:
                user_input = input("\nPress ENTER to fill survey, or 'q' to quit > ").strip().lower()
            except EOFError:
                break

            if user_input == "q":
                break

            result = bot.fill_survey(rating_choice=rating, comment_text=comment)

            if result["success"]:
                print(
                    f"\n  ✅ SUCCESS — Filled "
                    f"{result['radios']} radio group(s), "
                    f"{result['texts']} text field(s), "
                    f"{result['selects']} dropdown(s)."
                )
                print("  Review the answers in the browser, then click Submit.")
            else:
                print(
                    "\n  ❌ Fill did not complete successfully. "
                    "A screenshot was saved to ./debug_screenshots/ for debugging."
                )

        print("\n  Exiting session…")

    except KeyboardInterrupt:
        print("\n\n  Stopped by user (Ctrl+C).")

    finally:
        bot.close()


if __name__ == "__main__":
    main()