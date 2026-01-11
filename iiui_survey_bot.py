import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Try to import dotenv for .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class IIUISurveyBot:
    def __init__(self, registration_no=None, password=None, headless=False):
        self.registration_no = registration_no or os.getenv("IIUI_REG_NO")
        self.password = password or os.getenv("IIUI_PASSWORD")
        self.base_url = "https://erp.iiui.edu.pk/student/login"
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except ImportError:
            self.driver = webdriver.Chrome(options=chrome_options)
            
        self.wait = WebDriverWait(self.driver, 15)

    def login(self):
        if not self.registration_no or not self.password:
            logger.error("Credentials not found! Please set IIUI_REG_NO and IIUI_PASSWORD in .env file.")
            return False

        try:
            logger.info("Navigating to login page...")
            self.driver.get(self.base_url)
            
            reg_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            reg_field.send_keys(self.registration_no)
            
            pass_field = self.driver.find_element(By.ID, "password")
            pass_field.send_keys(self.password)
            
            login_btn = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            login_btn.click()
            
            logger.info("Login credentials submitted.")
            return True
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    def fill_survey(self, rating_choice="Strongly Agree", comment_text="I filled this survey using my personal Agent, Thank you"):
        try:
            logger.info("Scanning page structure...")
            
            # 1. Handle Radio Buttons using JavaScript
            self.driver.execute_script("""
                const ratingChoice = arguments[0].toLowerCase();
                const radios = document.querySelectorAll('input[type="radio"]');
                const groups = {};
                
                radios.forEach(radio => {
                    const name = radio.name;
                    if (name) {
                        if (!groups[name]) groups[name] = [];
                        groups[name].push(radio);
                    }
                });

                Object.values(groups).forEach(options => {
                    let clicked = false;
                    for (const opt of options) {
                        const label = document.querySelector('label[for="' + opt.id + '"]') || 
                                      (opt.nextElementSibling && opt.nextElementSibling.tagName === 'LABEL' ? opt.nextElementSibling : null);
                        
                        if (label && label.innerText.toLowerCase().includes(ratingChoice)) {
                            opt.click();
                            clicked = true;
                            break;
                        }
                    }
                    if (!clicked && options.length > 0) {
                        options[0].click();
                    }
                });
            """, rating_choice)

            # 2. Handle ALL Text Inputs and Textareas using JavaScript
            filled_count = self.driver.execute_script("""
                const commentText = arguments[0];
                const textElements = document.querySelectorAll('textarea, input[type="text"]');
                let count = 0;
                
                textElements.forEach(el => {
                    if (el.id !== 'search-friends' && el.offsetWidth > 0 && el.offsetHeight > 0) {
                        el.value = commentText;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        count++;
                    }
                });
                return count;
            """, comment_text)
            
            logger.info(f"Successfully filled all questions and {filled_count} comment fields.")
            return True

        except Exception as e:
            logger.error(f"Error during fill: {str(e)}")
            return False

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    # Configuration
    DEFAULT_RATING = "Strongly Agree"
    DEFAULT_COMMENT = "I filled this survey using my personal Agent, Thank you"

    bot = IIUISurveyBot()
    try:
        if bot.login():
            while True:
                print("\n" + "="*60)
                print("READY TO FILL SURVEY")
                print("1. Navigate to the survey page in the browser.")
                print("2. Once the questions are visible, come back here.")
                print("="*60)
                
                user_input = input("\nPress ENTER to fill this survey, or type 'q' to quit > ").strip().lower()
                
                if user_input == 'q':
                    break
                
                if bot.fill_survey(rating_choice=DEFAULT_RATING, comment_text=DEFAULT_COMMENT):
                    print("\n[SUCCESS] Survey filled! Review and click 'Submit' on the page.")
                    print("After submitting, you can navigate to another survey and repeat.")
                else:
                    print("\n[ERROR] Something went wrong during filling. Please try again.")
            
            print("\nExiting session...")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        bot.close()