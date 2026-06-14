"""
IIUI Survey Bot — Full Automation Edition
Logs in, discovers ALL pending surveys, fills every form, and submits automatically.

Usage:
    python3 iiui_survey_bot.py

Configuration (via .env):
    IIUI_REG_NO        — Your registration number
    IIUI_PASSWORD      — Your ERP password
    IIUI_HEADLESS      — "true" to hide the browser (default: false)
    IIUI_WAIT_TIMEOUT  — Page timeout in seconds (default: 20)
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
    UnexpectedAlertPresentException,
    NoAlertPresentException,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Retry decorator ────────────────────────────────────────────────────────────
def retry(max_attempts=3, delay=2.0, exceptions=(Exception,)):
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
                        logger.error(f"[{func.__name__}] All {max_attempts} attempts failed.")
            raise last_exc
        return wrapper
    return decorator


# ── Rating menu ────────────────────────────────────────────────────────────────
RATING_OPTIONS = ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"]


def prompt_rating() -> str:
    print("\n" + "═" * 58)
    print("  SELECT RATING FOR ALL SURVEY QUESTIONS")
    print("═" * 58)
    for i, opt in enumerate(RATING_OPTIONS, 1):
        print(f"  {i}. {opt}")
    print("  (Press ENTER for default: Strongly Agree)")
    print("═" * 58)
    while True:
        choice = input("  Your choice [1-5]: ").strip()
        if choice == "":
            return RATING_OPTIONS[0]
        if choice.isdigit() and 1 <= int(choice) <= 5:
            return RATING_OPTIONS[int(choice) - 1]
        print("  ⚠  Enter a number 1-5.")


# ══════════════════════════════════════════════════════════════════════════════
class IIUISurveyBot:
    """Fully automatic IIUI ERP survey bot."""

    LOGIN_URL   = "https://erp.iiui.edu.pk/student/login"
    SURVEY_URL  = "https://erp.iiui.edu.pk/student/student-survey"
    DASHBOARD_FRAGMENT = "/student/dashboard"

    _REG_SELECTORS = [
        (By.ID,          "email"),
        (By.NAME,        "email"),
        (By.NAME,        "username"),
        (By.CSS_SELECTOR,"input[type='email']"),
        (By.CSS_SELECTOR,"input[placeholder*='egistration']"),
        (By.CSS_SELECTOR,"input[placeholder*='mail']"),
    ]
    _PASS_SELECTORS = [
        (By.ID,          "password"),
        (By.NAME,        "password"),
        (By.CSS_SELECTOR,"input[type='password']"),
    ]
    _LOGIN_BTN_SELECTORS = [
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login')]"),
        (By.XPATH, "//input[contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login')]"),
    ]
    _SUBMIT_BTN_SELECTORS = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit')]"),
        (By.XPATH, "//input[@type='submit']"),
        (By.CSS_SELECTOR, ".btn-primary[type='submit']"),
        (By.CSS_SELECTOR, ".btn-success[type='submit']"),
        (By.XPATH, "//button[contains(@class,'btn') and not(contains(@class,'back')) and not(contains(@class,'cancel'))]"),
    ]
    _ERROR_SELECTORS = [
        (By.CSS_SELECTOR, ".alert-danger"),
        (By.CSS_SELECTOR, ".alert-error"),
        (By.CSS_SELECTOR, "[class*='error']"),
        (By.CSS_SELECTOR, ".invalid-feedback"),
    ]
    # Selectors that identify a pending (unfilled) survey link in the action column
    _PENDING_LINK_SELECTORS = [
        "td a[href*='evaluation']",
        "td a[href*='survey']",
        "td a[href*='fill']",
        "td a[href*='course']",
        "td a[href*='teacher']",
        "td .btn:not(.badge)",
        "td a.btn",
        "td a:not([class*='badge'])",
    ]
    # Text that means the survey is already done — skip these
    _SUBMITTED_TEXTS = {"response submitted", "submitted", "completed", "filled"}

    # ── Init ───────────────────────────────────────────────────────────────────
    def __init__(self, reg_no=None, password=None, headless=None, timeout=None):
        self.driver = None

        # Direct params take priority over env vars
        self.reg_no   = (reg_no   or os.getenv("IIUI_REG_NO",   "")).strip()
        self.password = (password or os.getenv("IIUI_PASSWORD",  "")).strip()

        if headless is None:
            # Always headless on cloud / CI (no display available)
            headless = os.getenv("IIUI_HEADLESS", "false").lower() == "true" or self._is_cloud()
        if timeout is None:
            timeout = int(os.getenv("IIUI_WAIT_TIMEOUT", "20"))
        self.timeout = timeout

        self._ss_dir = Path("debug_screenshots")
        self._ss_dir.mkdir(exist_ok=True)

        opts = Options()
        # Always headless when running on cloud (no display)
        if headless or self._is_cloud():
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--window-size=1280,900")
        opts.add_argument("--log-level=3")
        opts.add_argument("--remote-debugging-port=9222")
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])

        try:
            self.driver = self._init_driver(opts)
            self.wait = WebDriverWait(self.driver, self.timeout)
            logger.info(f"Browser ready. (timeout={self.timeout}s, headless={headless})")
        except WebDriverException as exc:
            logger.error(f"ChromeDriver failed to start: {exc}")
            raise

    @staticmethod
    def _is_cloud() -> bool:
        """Detect Streamlit Cloud / CI — no display available."""
        return (
            os.getenv("STREAMLIT_SHARING_MODE") is not None   # Streamlit Cloud
            or os.getenv("CI") is not None                     # GitHub Actions / CI
            or not os.getenv("DISPLAY", "")                    # No X display (Linux cloud)
        )

    @staticmethod
    def _init_driver(opts: Options):
        """
        Try to start a Chrome/Chromium driver in this order:
          1. System Chromium (Streamlit Cloud / Linux servers)
          2. webdriver-manager managed Chrome (local dev)
          3. Bare system chromedriver (fallback)
        """
        CHROMIUM_BINS = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]
        CHROMEDRIVER_BINS = [
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
        ]

        # 1 ── System Chromium (cloud)
        for binary in CHROMIUM_BINS:
            if Path(binary).exists():
                logger.info(f"Using system Chromium: {binary}")
                opts.binary_location = binary
                # Find matching chromedriver
                for driver_bin in CHROMEDRIVER_BINS:
                    if Path(driver_bin).exists():
                        return webdriver.Chrome(
                            service=Service(driver_bin), options=opts
                        )
                # chromedriver not at known path — try bare
                try:
                    return webdriver.Chrome(options=opts)
                except Exception:
                    pass

        # 2 ── webdriver-manager (local Chrome)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            logger.info("Launching Chrome via webdriver-manager…")
            return webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=opts
            )
        except ImportError:
            pass

        # 3 ── Bare system chromedriver
        logger.warning("webdriver-manager not found — using system chromedriver.")
        return webdriver.Chrome(options=opts)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _ss(self, label: str):
        if self.driver is None:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self._ss_dir / f"{ts}_{label}.png"
        try:
            self.driver.save_screenshot(str(path))
            logger.info(f"📸 {path}")
        except Exception:
            pass

    def _find_first(self, selectors, timeout=5):
        for by, val in selectors:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, val))
                )
            except (TimeoutException, NoSuchElementException):
                continue
        return None

    def _wait_ready(self, extra=0.5):
        """Wait for document.readyState == complete, then a short settle."""
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass
        time.sleep(extra)

    def _dismiss_alert(self, accept=True) -> str | None:
        """Accept or dismiss any open JS alert/confirm. Returns its text."""
        try:
            alert = self.driver.switch_to.alert
            text = alert.text
            if accept:
                alert.accept()
            else:
                alert.dismiss()
            logger.info(f"  ✔ Alert handled: \"{text}\"")
            return text
        except NoAlertPresentException:
            return None

    def _detect_login_error(self):
        for by, sel in self._ERROR_SELECTORS:
            try:
                for el in self.driver.find_elements(by, sel):
                    t = el.text.strip()
                    if t:
                        return t
            except Exception:
                pass
        return None

    # ── Login ──────────────────────────────────────────────────────────────────
    @retry(max_attempts=3, delay=3.0, exceptions=(WebDriverException, TimeoutException))
    def login(self) -> bool:
        if not self.reg_no or not self.password:
            logger.error("Credentials missing! Set IIUI_REG_NO and IIUI_PASSWORD in .env")
            return False

        logger.info(f"Opening login page…")
        self.driver.get(self.LOGIN_URL)

        reg = self._find_first(self._REG_SELECTORS, timeout=self.timeout)
        if not reg:
            self._ss("no_reg_field")
            logger.error("Registration field not found on login page.")
            return False
        reg.clear(); reg.send_keys(self.reg_no)

        pwd = self._find_first(self._PASS_SELECTORS, timeout=5)
        if not pwd:
            self._ss("no_pass_field")
            logger.error("Password field not found.")
            return False
        pwd.clear(); pwd.send_keys(self.password)

        btn = self._find_first(self._LOGIN_BTN_SELECTORS, timeout=5)
        if not btn:
            self._ss("no_login_btn")
            logger.error("Login button not found.")
            return False
        btn.click()
        logger.info("Credentials submitted, awaiting response…")

        # Wait for URL to change away from login page
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: d.current_url != self.LOGIN_URL
            )
        except TimeoutException:
            pass

        url = self.driver.current_url
        if self.DASHBOARD_FRAGMENT in url or "login" not in url.lower():
            logger.info(f"✅ Login successful! ({url})")
            return True

        err = self._detect_login_error()
        if err:
            self._ss("login_error")
            logger.error(f"❌ Login failed — Portal: \"{err}\"")
            return False

        self._ss("login_unknown")
        logger.error(f"❌ Login failed — still on login page. Check credentials.")
        return False

    # ── Discover pending surveys ───────────────────────────────────────────────
    def _get_pending_links(self) -> list[dict]:
        """
        Scan the survey table and return all pending (not-yet-submitted)
        survey entries as a list of dicts:
            {"href": str, "text": str, "row_info": str}
        """
        pending = []
        try:
            # Wait for the table to appear
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
        except TimeoutException:
            logger.warning("No table found on survey listing page.")
            return pending

        rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        logger.info(f"  Found {len(rows)} course row(s) in survey table.")

        for row in rows:
            # Collect row description (course name)
            cells = row.find_elements(By.TAG_NAME, "td")
            row_info = cells[3].text.strip() if len(cells) > 3 else "Unknown Course"

            # Look for action cell (last td)
            action_td = cells[-1] if cells else None
            if action_td is None:
                continue

            # Find any <a> or <button> that is NOT a "Response Submitted" badge
            clickables = action_td.find_elements(By.CSS_SELECTOR, "a, button")
            for el in clickables:
                text = el.text.strip()
                href = el.get_attribute("href") or ""
                cls  = el.get_attribute("class") or ""

                # Skip already-submitted badges
                if text.lower() in self._SUBMITTED_TEXTS:
                    continue
                if "badge" in cls.lower() and "submitted" in text.lower():
                    continue
                if not text and not href:
                    continue

                pending.append({
                    "element": el,
                    "href": href,
                    "text": text or "Evaluation Link",
                    "row_info": row_info,
                })

        return pending

    # ── Fill survey form ───────────────────────────────────────────────────────
    def _fill_form(self, rating: str, comment: str) -> dict:
        result = {"radios": 0, "texts": 0, "selects": 0}

        # Wait for form fields
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='radio'], textarea, select")
                )
            )
        except TimeoutException:
            self._ss("no_form_fields")
            logger.warning("  ⚠ No form fields detected on survey page.")
            return result

        # 1. Radio buttons
        result["radios"] = self.driver.execute_script("""
            const choice = arguments[0].toLowerCase().trim();
            const radios = document.querySelectorAll('input[type="radio"]');
            const groups = {};
            radios.forEach(r => {
                if (r.name) {
                    if (!groups[r.name]) groups[r.name] = [];
                    groups[r.name].push(r);
                }
            });
            let filled = 0;
            Object.values(groups).forEach(opts => {
                let clicked = false;
                for (const opt of opts) {
                    const lbl =
                        (opt.id && document.querySelector('label[for="'+opt.id+'"]')) ||
                        (opt.nextElementSibling && opt.nextElementSibling.tagName==='LABEL'
                            ? opt.nextElementSibling : null) ||
                        opt.closest('label');
                    const lblTxt = lbl ? lbl.innerText.toLowerCase().trim() : '';
                    const val    = opt.value ? opt.value.toLowerCase().trim() : '';
                    if (lblTxt.includes(choice) || val.includes(choice)) {
                        opt.checked = true;
                        opt.dispatchEvent(new MouseEvent('click',  {bubbles:true}));
                        opt.dispatchEvent(new Event('input',  {bubbles:true}));
                        opt.dispatchEvent(new Event('change', {bubbles:true}));
                        clicked = true; filled++; break;
                    }
                }
                if (!clicked && opts.length > 0) {
                    opts[0].checked = true;
                    opts[0].dispatchEvent(new MouseEvent('click',  {bubbles:true}));
                    opts[0].dispatchEvent(new Event('input',  {bubbles:true}));
                    opts[0].dispatchEvent(new Event('change', {bubbles:true}));
                    filled++;
                }
            });
            return filled;
        """, rating) or 0

        # 2. Text inputs / textareas
        result["texts"] = self.driver.execute_script("""
            const text  = arguments[0];
            const skip  = new Set(['search','q','search-friends']);
            const els   = document.querySelectorAll(
                'textarea, input[type="text"], input[type="search"]'
            );
            let count = 0;
            els.forEach(el => {
                if (skip.has(el.id)) return;
                if (el.offsetWidth===0 && el.offsetHeight===0) return;
                if (el.readOnly || el.disabled) return;
                const proto = el.tagName==='TEXTAREA'
                    ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(proto,'value');
                if (setter && setter.set) setter.set.call(el, text);
                else el.value = text;
                el.dispatchEvent(new Event('input',  {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                el.dispatchEvent(new Event('blur',   {bubbles:true}));
                count++;
            });
            return count;
        """, comment) or 0

        # 3. Select dropdowns
        result["selects"] = self.driver.execute_script("""
            const choice = arguments[0].toLowerCase().trim();
            const sels = document.querySelectorAll('select');
            let count = 0;
            sels.forEach(sel => {
                if (sel.disabled || sel.offsetWidth===0) return;
                let matched = false;
                for (const opt of sel.options) {
                    if (opt.text.toLowerCase().trim().includes(choice)) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change',{bubbles:true}));
                        matched = true; count++; break;
                    }
                }
                if (!matched && sel.options.length > 1) {
                    sel.value = sel.options[1].value;
                    sel.dispatchEvent(new Event('change',{bubbles:true}));
                    count++;
                }
            });
            return count;
        """, rating) or 0

        return result

    # ── Submit form ────────────────────────────────────────────────────────────
    def _submit_form(self) -> bool:
        """Click the submit button and handle any confirmation dialog."""
        btn = self._find_first(self._SUBMIT_BTN_SELECTORS, timeout=10)
        if btn is None:
            self._ss("no_submit_btn")
            logger.error("  ❌ Submit button not found.")
            return False

        logger.info(f"  Clicking submit: \"{btn.text or btn.get_attribute('value')}\"")
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.3)
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)

        time.sleep(1.0)  # Give JS time to fire any alert

        # Handle browser confirm/alert dialog
        alert_text = self._dismiss_alert(accept=True)

        # Wait for redirect or success indicator
        url_before = self.driver.current_url
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: (
                    d.current_url != url_before or
                    len(d.find_elements(By.CSS_SELECTOR,
                        ".alert-success, .success, [class*='success']")) > 0
                )
            )
        except TimeoutException:
            pass  # Might still have succeeded

        # Dismiss any second alert (e.g. "Survey submitted successfully!")
        self._dismiss_alert(accept=True)

        # Check for success message on page
        success_indicators = [
            ".alert-success", ".alert-info",
            "[class*='success']", "[class*='thank']",
        ]
        for sel in success_indicators:
            try:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.text.strip():
                        logger.info(f"  ✔ Portal confirmation: \"{el.text.strip()[:80]}\"")
                        return True
            except Exception:
                pass

        # If URL changed away from the form, that's also a success signal
        if self.driver.current_url != url_before:
            logger.info(f"  ✔ Redirected after submit → {self.driver.current_url}")
            return True

        logger.warning("  ⚠ Submit clicked but no clear success signal detected.")
        self._ss("submit_uncertain")
        return True  # Optimistic — let the loop continue

    # ── Main automation loop ───────────────────────────────────────────────────
    def complete_all_surveys(self, rating: str, comment: str) -> dict:
        """
        Navigate to the survey listing, find every pending survey link,
        fill it, submit it, and repeat until none remain.

        Returns a summary dict.
        """
        summary = {"completed": 0, "skipped": 0, "failed": 0, "already_done": 0}

        logger.info(f"Navigating to survey listing: {self.SURVEY_URL}")
        self.driver.get(self.SURVEY_URL)
        self._wait_ready()
        self._ss("survey_listing")

        max_passes = 20  # safety cap
        for pass_num in range(1, max_passes + 1):
            pending = self._get_pending_links()

            if not pending:
                logger.info("✅ No more pending surveys found — all done!")
                break

            logger.info(f"\n── Pass {pass_num}: {len(pending)} pending survey(s) ──")

            # Process only the FIRST pending link per pass (page reloads after submit)
            entry = pending[0]
            course = entry["row_info"]
            text   = entry["text"]
            href   = entry["href"]
            logger.info(f"  → [{text}] for: {course}")
            logger.info(f"    URL: {href}")

            try:
                # Navigate to the survey form
                if href and href.startswith("http"):
                    self.driver.get(href)
                else:
                    # Click the element directly
                    try:
                        entry["element"].click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", entry["element"])

                self._wait_ready(extra=1.0)
                self._ss(f"form_{pass_num}_{text[:20].replace(' ','_')}")

                # Scroll to top so all fields are accessible
                self.driver.execute_script("window.scrollTo(0,0);")

                # Fill the form
                counts = self._fill_form(rating, comment)
                total_filled = counts["radios"] + counts["texts"] + counts["selects"]
                logger.info(
                    f"  ✔ Filled — radios:{counts['radios']} "
                    f"texts:{counts['texts']} selects:{counts['selects']}"
                )

                if total_filled == 0:
                    logger.warning("  ⚠ Nothing was filled. Skipping submit.")
                    summary["skipped"] += 1
                    self.driver.get(self.SURVEY_URL)
                    self._wait_ready()
                    continue

                # Small pause so the page registers all inputs
                time.sleep(0.5)

                # Submit
                submitted = self._submit_form()
                if submitted:
                    summary["completed"] += 1
                    logger.info(f"  ✅ Submitted! ({course} — {text})")
                else:
                    summary["failed"] += 1
                    logger.error(f"  ❌ Submit failed for: {course} — {text}")

            except Exception as exc:
                self._ss(f"error_pass{pass_num}")
                logger.error(f"  ❌ Unexpected error: {exc}")
                logger.debug(traceback.format_exc())
                summary["failed"] += 1

            # Go back to survey listing for the next pass
            self._wait_ready(extra=0.5)
            if self.SURVEY_URL not in self.driver.current_url:
                self.driver.get(self.SURVEY_URL)
                self._wait_ready()

        self._ss("final_state")
        return summary

    # ── Close ──────────────────────────────────────────────────────────────────
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed.")
            except Exception:
                pass
            self.driver = None


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    print("═" * 58)
    print("    IIUI SURVEY BOT — Full Automation Edition")
    print("═" * 58)

    rating  = prompt_rating()
    comment = "I filled this survey using my personal Agent, Thank you"

    print(f"\n  Rating  : {rating}")
    print(f"  Comment : {comment}\n")

    headless = os.getenv("IIUI_HEADLESS", "false").lower() == "true"

    try:
        bot = IIUISurveyBot(headless=headless)
    except WebDriverException:
        print("\n[FATAL] Chrome could not start. See error above.")
        sys.exit(1)

    try:
        # Step 1: Login
        if not bot.login():
            print("\n[FATAL] Login failed. Check .env credentials.")
            sys.exit(1)

        # Step 2: Run full automation
        print("\n" + "═" * 58)
        print("  Scanning for pending surveys and filling automatically…")
        print("  (Screenshots saved to ./debug_screenshots/ on any issue)")
        print("═" * 58 + "\n")

        summary = bot.complete_all_surveys(rating=rating, comment=comment)

        # Step 3: Print summary
        print("\n" + "═" * 58)
        print("  SURVEY BOT COMPLETE — SUMMARY")
        print("═" * 58)
        print(f"  ✅ Completed & submitted : {summary['completed']}")
        print(f"  ⏭  Skipped (no fields)   : {summary['skipped']}")
        print(f"  ❌ Failed                : {summary['failed']}")
        print("═" * 58)

        if summary["completed"] == 0 and summary["failed"] == 0:
            print("\n  ℹ  All surveys were already submitted — nothing to do!")

    except KeyboardInterrupt:
        print("\n\n  Stopped by user (Ctrl+C).")

    finally:
        bot.close()


if __name__ == "__main__":
    main()