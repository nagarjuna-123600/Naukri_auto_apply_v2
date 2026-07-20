"""
Naukri Auto Apply Bot V2
========================
Features:
  ✅ Cookie-based login (email/password fallback)
  ✅ Daily name alternation (Pulabala Nagarjuna / Nagarjuna Pulabala)
  ✅ Section 0 — New jobs & internships (last 24 hrs)
  ✅ Section 1 — Hyderabad office jobs
  ✅ Section 2 — Hyderabad internships
  ✅ Section 3 — Remote/WFH jobs
  ✅ Section 4 — Remote/WFH internships
  ✅ IT-only strict filter
  ✅ Required skills match
  ✅ Save redirect jobs on Naukri Saved Jobs
  ✅ Duplicate prevention (applied_jobs.json)
  ✅ Headless Chrome + Stealth mode
  ✅ GitHub Actions every 4 hours
"""

import os
import json
import time
import logging
from datetime import datetime, date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ═══════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s ***%(levelname)s*** %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("naukri_bot.log"),
    ],
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
CONFIG = {
    # ── Credentials (from GitHub Secrets) ──────────────────────
    "email":    os.environ.get("NAUKRI_EMAIL", ""),
    "password": os.environ.get("NAUKRI_PASSWORD", ""),

    # ── Location ────────────────────────────────────────────────
    "location": "Hyderabad",

    # ── Job search keywords ─────────────────────────────────────
    "search_keywords": [
        "Java Developer",
        "Python Developer",
        "SQL Developer",
        "Software Engineer",
        "Associate Software Engineer",
        "Customer Software Engineer",
        "Data Analyst",
        "AI ML Engineer",
    ],

    # ── Internship keywords ─────────────────────────────────────
    "internship_keywords": [
        "Java Intern",
        "Python Intern",
        "SQL Intern",
        "AIML Intern",
        "Software Engineer Intern",
        "Data Analyst Intern",
    ],

    # ── Skills filter ───────────────────────────────────────────
    "required_skills": [
        "java", "python", "sql", "mysql", "postgresql",
        "software engineer", "associate software engineer",
        "customer software engineer", "software developer",
        "langchain", "rag", "huggingface", "faiss", "streamlit",
        "junior developer", "trainee", "intern", "fresher",
        "java developer", "python developer", "sql developer",
        "ai", "ml", "machine learning", "deep learning",
        "data analyst", "data science",
    ],

    # ── Exclude keywords ────────────────────────────────────────
    "exclude_keywords": [
        "senior", "lead", "manager", "architect",
        "web developer", "frontend developer", "front-end developer",
        "backend developer", "back-end developer",
        "full stack developer", "fullstack developer",
        "civil engineer", "mechanical engineer", "electrical engineer",
        "hardware engineer", "site engineer", "site supervisor",
        "electronics engineer", "embedded engineer",
        "production engineer", "manufacturing engineer",
        "automobile engineer", "aeronautical engineer",
        "structural engineer", "design engineer",
    ],

    # ── IT keywords (strict filter) ──────────────────────────────
    "it_keywords": [
        "software", "developer", "engineer", "programmer",
        "java", "python", "sql", "data", "analyst", "ml", "ai",
        "machine learning", "artificial intelligence", "deep learning",
        "nlp", "langchain", "rag", "streamlit", "cloud", "devops",
        "database", "mysql", "postgresql", "mongodb",
        "it ", "information technology", "computer", "tech",
        "intern", "trainee", "fresher", "associate", "junior",
        "automation", "testing", "qa", "quality assurance",
        "cybersecurity", "api", "aws", "azure", "gcp",
        "docker", "kubernetes", "linux", "windows",
    ],

    # ── Internship settings ─────────────────────────────────────
    "min_stipend": 10000,

    # ── Bot settings ─────────────────────────────────────────────
    "max_apply_per_search": 10,
    "action_delay": 2,
    "log_file": "applied_jobs.json",
    "manual_log_file": "manual_apply_jobs.json",
    "headless": False,
}

# ═══════════════════════════════════════════════════════════════
#  APPLIED JOBS TRACKER
# ═══════════════════════════════════════════════════════════════
def load_applied(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_applied(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ═══════════════════════════════════════════════════════════════
#  MANUAL APPLY JOBS TRACKER
# ═══════════════════════════════════════════════════════════════
def save_manual_job(job_url, job_title, reason):
    path = CONFIG["manual_log_file"]
    data = load_applied(path)
    if job_url not in data:
        data[job_url] = {
            "title": job_title,
            "reason": reason,
            "saved_at": datetime.now().isoformat(),
        }
        save_applied(path, data)
        log.info(f"  📋 Logged to manual_apply_jobs.json: {job_title}")

# ═══════════════════════════════════════════════════════════════
#  CHROME DRIVER
# ═══════════════════════════════════════════════════════════════
def create_driver():
    options = webdriver.ChromeOptions()

    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

    if is_ci or CONFIG["headless"]:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        log.info("  Running in headless mode")
    else:
        options.add_argument("--start-maximized")
        log.info("  Running in visible mode")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)

    # Stealth JS
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins',  {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages',{get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        window.chrome = {runtime: {}};
    """})
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(3)
    return driver

# ═══════════════════════════════════════════════════════════════
#  POPUP DISMISSER
# ═══════════════════════════════════════════════════════════════
def dismiss_popups(driver, timeout=3):
    CLOSE_SELECTORS = [
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'skip')]",
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'maybe later')]",
        "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'not now')]",
        "//*[contains(@class,'close-btn') or contains(@class,'closeBtn') or contains(@class,'cross-btn')]",
        "//*[contains(@class,'crossIcon') or contains(@class,'cross-icon')]",
        "//*[contains(@class,'modal-close') or contains(@class,'modalClose')]",
        "//button[@aria-label='Close' or @aria-label='close' or @aria-label='Dismiss']",
        "//*[@data-testid='modal-close']",
        "//button[normalize-space(text())='×' or normalize-space(text())='✕']",
    ]
    dismissed = 0
    for sel in CLOSE_SELECTORS:
        try:
            els = driver.find_elements(By.XPATH, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.5)
                    dismissed += 1
                    break
        except Exception:
            continue
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass
    return dismissed

# ═══════════════════════════════════════════════════════════════
#  COOKIE LOGIN
# ═══════════════════════════════════════════════════════════════
def login_with_cookies(driver):
    cookies_json = os.environ.get("NAUKRI_COOKIES", "")
    if not cookies_json:
        log.info("No NAUKRI_COOKIES found")
        return False
    try:
        cookies = json.loads(cookies_json)
        driver.get("https://www.naukri.com")
        time.sleep(3)
        driver.delete_all_cookies()
        for cookie in cookies:
            try:
                c = {
                    "name":   cookie["name"],
                    "value":  cookie["value"],
                    "domain": cookie.get("domain", ".naukri.com"),
                    "path":   cookie.get("path", "/"),
                    "secure": cookie.get("secure", False),
                }
                if "expirationDate" in cookie and not cookie.get("session", False):
                    c["expiry"] = int(cookie["expirationDate"])
                driver.add_cookie(c)
            except Exception:
                continue
        driver.get("https://www.naukri.com/mnjuser/homepage")
        time.sleep(4)
        dismiss_popups(driver)
        if "homepage" in driver.current_url or "mnjuser" in driver.current_url:
            log.info("✅ Cookie login successful!")
            return True
        return False
    except Exception as e:
        log.error(f"Cookie login error: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
#  EMAIL/PASSWORD LOGIN
# ═══════════════════════════════════════════════════════════════
def login(driver, email, password):
    if login_with_cookies(driver):
        return True

    log.info("Trying email/password login...")
    driver.get("https://www.naukri.com/nlogin/login")
    wait = WebDriverWait(driver, 20)
    time.sleep(5)
    try:
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "usernameField")))
        driver.execute_script("arguments[0].click();", email_field)
        email_field.clear()
        for char in email:
            email_field.send_keys(char)
            time.sleep(0.05)
        time.sleep(1)

        pwd_field = wait.until(EC.element_to_be_clickable((By.ID, "passwordField")))
        driver.execute_script("arguments[0].click();", pwd_field)
        pwd_field.clear()
        for char in password:
            pwd_field.send_keys(char)
            time.sleep(0.05)
        time.sleep(1)

        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        driver.execute_script("arguments[0].click();", login_btn)
        wait.until(EC.url_contains("naukri.com"))
        time.sleep(CONFIG["action_delay"])
        log.info("✅ Email/password login successful!")
        dismiss_popups(driver)
        return True
    except TimeoutException:
        log.error("Login failed!")
        return False

# ═══════════════════════════════════════════════════════════════
#  DAILY NAME UPDATE
# ═══════════════════════════════════════════════════════════════
def update_profile_name(driver):
    profile_flag = "profile_updated_date.txt"
    today_str = str(date.today())

    # Check if already updated today
    if os.path.exists(profile_flag):
        with open(profile_flag) as f:
            if f.read().strip() == today_str:
                log.info("  Profile name already updated today — skipping")
                return

    day_number = date.today().toordinal()
    is_odd_day = day_number % 2 == 1
    name_today = "Pulabala Nagarjuna" if is_odd_day else "Nagarjuna Pulabala"
    log.info(f"  Today's name ({'odd' if is_odd_day else 'even'} day): {name_today}")

    try:
        driver.get("https://www.naukri.com/mnjuser/profile?id=&altresid")
        time.sleep(4)
        dismiss_popups(driver)

        # Click edit icon
        try:
            edit_icon = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//span[contains(@class,'naukicon-edit')] | "
                    "//i[contains(@class,'naukicon-edit')] | "
                    "//*[@data-ga-track='basicDetailEdit'] | "
                    "//div[contains(@class,'basic')]//span[contains(@class,'edit')]"
                ))
            )
            driver.execute_script("arguments[0].click();", edit_icon)
            time.sleep(3)
        except TimeoutException:
            driver.execute_script("""
                var btns = document.querySelectorAll('[class*="edit"],[class*="Edit"]');
                for(var b of btns){if(b.offsetParent!==null){b.click();break;}}
            """)
            time.sleep(3)

        # Update Full name field
        name_field = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH,
                "//input[@placeholder='Full name' or @name='fullName' or @id='fullName']"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", name_field)
        time.sleep(0.5)
        name_field.clear()
        for char in name_today:
            name_field.send_keys(char)
            time.sleep(0.05)
        time.sleep(0.5)

        # Click Save
        save_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[normalize-space(text())='Save' or normalize-space(text())='save']"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
        driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(2)
        log.info(f"  ✅ Name updated to: {name_today}")

        # Save flag
        with open(profile_flag, "w") as f:
            f.write(today_str)

    except Exception as e:
        log.warning(f"  Name update failed (non-critical): {e}")

# ═══════════════════════════════════════════════════════════════
#  JOB MATCHING
# ═══════════════════════════════════════════════════════════════
def is_it_job(title):
    title_lower = title.lower()
    return any(kw in title_lower for kw in CONFIG["it_keywords"])

def is_matching_job(title, description):
    title_lower = title.lower()
    desc_lower  = description.lower()

    # Strict IT-only filter
    if not is_it_job(title):
        log.info(f"  Skipping (not IT): {title}")
        return False

    # Exclude keywords
    for ex in CONFIG["exclude_keywords"]:
        if ex.lower() in title_lower:
            log.info(f"  Skipping (excluded '{ex}'): {title}")
            return False

    # Data Analyst only with SQL
    if "data analyst" in title_lower:
        if "sql" not in title_lower and "sql" not in desc_lower:
            log.info(f"  Skipping Data Analyst (no SQL): {title}")
            return False
        return True

    # Required skills
    for skill in CONFIG["required_skills"]:
        if skill.lower() in title_lower or skill.lower() in desc_lower:
            return True

    log.info(f"  Skipping (no skill match): {title}")
    return False

def extract_stipend(text):
    import re
    if not text:
        return 0
    nums = re.findall(r'\d[\d,]*', text.replace(" ", ""))
    for n in nums:
        val = int(n.replace(",", ""))
        if val >= 1000:
            return val
    return 0

def is_matching_internship(title, description, stipend_text):
    title_lower = title.lower()
    desc_lower  = description.lower()

    # Strict IT-only filter
    if not is_it_job(title):
        log.info(f"  Skipping internship (not IT): {title}")
        return False

    # Exclude keywords
    for ex in CONFIG["exclude_keywords"]:
        if ex.lower() in title_lower:
            log.info(f"  Skipping internship (excluded '{ex}'): {title}")
            return False

    # Skills match
    skill_match = any(
        s in title_lower or s in desc_lower
        for s in CONFIG["required_skills"]
    )
    if not skill_match:
        log.info(f"  Skipping internship (no skill match): {title}")
        return False

    # Stipend check
    stipend = extract_stipend(stipend_text)
    if stipend < CONFIG["min_stipend"]:
        log.info(f"  Skipping internship (stipend ₹{stipend:,} < ₹{CONFIG['min_stipend']:,}): {title}")
        return False

    return True

# ═══════════════════════════════════════════════════════════════
#  SAVE ON NAUKRI (redirect jobs)
# ═══════════════════════════════════════════════════════════════
def save_on_naukri(driver, job_url, job_title, original_window):
    try:
        driver.execute_script(f"window.open('{job_url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(3)
        dismiss_popups(driver)
        SAVE_SELECTORS = [
            "//button[contains(text(),'Save')]",
            "//a[contains(text(),'Save')]",
            "//*[contains(@class,'save-job')]",
            "//*[contains(@class,'saveJob')]",
            "//*[@title='Save Job']",
            "//span[contains(text(),'Save')]",
        ]
        for sel in SAVE_SELECTORS:
            try:
                btn = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", btn)
                log.info(f"  💾 Saved on Naukri (redirect): {job_title}")
                break
            except TimeoutException:
                continue
    except Exception as e:
        log.warning(f"  Could not save on Naukri: {e}")
    finally:
        try:
            driver.close()
            driver.switch_to.window(original_window)
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
#  APPLY TO JOB
# ═══════════════════════════════════════════════════════════════
def apply_to_job(driver, job_url, job_title, applied_log):
    if job_url in applied_log:
        log.info(f"  Already applied: {job_title}")
        return False

    original_window = driver.current_window_handle
    driver.execute_script(f"window.open('{job_url}', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(CONFIG["action_delay"])

    wait = WebDriverWait(driver, 10)

    try:
        dismiss_popups(driver)

        # Save on Naukri first (before applying)
        try:
            save_selectors = [
                "//button[contains(text(),'Save')]",
                "//*[contains(@class,'save-job')]",
                "//*[contains(@class,'saveJob')]",
                "//*[@title='Save Job']",
            ]
            for sel in save_selectors:
                try:
                    btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                    break
                except TimeoutException:
                    continue
        except Exception:
            pass

        # Find Apply button
        apply_btn = None
        for selector in [
            "//button[contains(text(),'Apply')]",
            "//a[contains(text(),'Apply')]",
            "//button[@id='apply-button']",
            "//*[contains(@class,'apply-button')]",
        ]:
            try:
                apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                break
            except TimeoutException:
                continue

        if not apply_btn:
            log.warning(f"  No Apply button: {job_title}")
            save_manual_job(job_url, job_title, "no_apply_button")
            driver.close()
            driver.switch_to.window(original_window)
            return False

        # Check for redirects before clicking
        REDIRECT_PATTERNS = {
            "company website": ["apply on company website", "apply via company", "visit company website"],
            "email": ["apply via email", "send cv", "email your cv", "send resume"],
            "whatsapp": ["apply via whatsapp", "whatsapp"],
        }
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        detected_reason = None
        for reason, patterns in REDIRECT_PATTERNS.items():
            if any(p in page_text for p in patterns):
                detected_reason = reason
                break

        # Check URL after click
        current_url = driver.current_url
        if not detected_reason and "naukri.com" not in current_url:
            detected_reason = "company website"

        if detected_reason:
            save_manual_job(job_url, job_title, detected_reason)
            save_on_naukri(driver, job_url, job_title, original_window)
            return False

        # Click Apply
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
        time.sleep(1)
        dismiss_popups(driver)
        try:
            apply_btn.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", apply_btn)
        log.info(f"  Clicked Apply: {job_title}")
        time.sleep(1.5)
        dismiss_popups(driver)

        # Confirm apply if needed
        try:
            confirm = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Apply')]"))
            )
            confirm.click()
            time.sleep(1)
        except TimeoutException:
            pass

        log.info(f"  ✅ Applied: {job_title}")
        applied_log[job_url] = {
            "title":      job_title,
            "applied_at": datetime.now().isoformat(),
            "url":        job_url,
        }
        driver.close()
        driver.switch_to.window(original_window)
        return True

    except ElementClickInterceptedException:
        log.warning(f"  Click blocked — saving: {job_title}")
        save_manual_job(job_url, job_title, "click_blocked")
        save_on_naukri(driver, job_url, job_title, original_window)
        return False

    except Exception as e:
        log.error(f"  Error applying to {job_title}: {e}")
        try:
            save_manual_job(job_url, job_title, f"error: {str(e)[:50]}")
            driver.close()
            driver.switch_to.window(original_window)
        except Exception:
            pass
        return False

# ═══════════════════════════════════════════════════════════════
#  SEARCH JOBS
# ═══════════════════════════════════════════════════════════════
def get_job_cards(driver, url):
    try:
        driver.get(url)
        time.sleep(CONFIG["action_delay"])
        dismiss_popups(driver)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
        cards = driver.find_elements(By.CLASS_NAME, "cust-job-tuple")
        return cards
    except Exception as e:
        log.warning(f"  Error loading page: {e}")
        return []

def get_card_details(card):
    try:
        try:
            title_el = card.find_element(By.CLASS_NAME, "title")
        except NoSuchElementException:
            title_el = card.find_element(By.TAG_NAME, "a")
        job_title = title_el.text.strip()
        job_url   = title_el.get_attribute("href") or card.find_element(By.TAG_NAME, "a").get_attribute("href")
        try:
            desc = card.find_element(By.CLASS_NAME, "job-description").text
        except NoSuchElementException:
            try:
                desc = card.find_element(By.CLASS_NAME, "job-desc").text
            except NoSuchElementException:
                desc = ""
        return job_title, job_url, desc
    except Exception:
        return None, None, ""

def get_stipend(card):
    try:
        return card.find_element(By.XPATH,
            ".//*[contains(@class,'stipend') or contains(@class,'salary')]"
        ).text
    except NoSuchElementException:
        return ""

# ═══════════════════════════════════════════════════════════════
#  PROCESS CARDS
# ═══════════════════════════════════════════════════════════════
def process_job_cards(driver, cards, applied_log, is_internship=False):
    applied = 0
    for card in cards:
        if applied >= CONFIG["max_apply_per_search"]:
            break
        try:
            job_title, job_url, desc = get_card_details(card)
            if not job_title or not job_url:
                continue

            log.info(f"  Checking: {job_title}")

            if is_internship:
                stipend_text = get_stipend(card)
                if not is_matching_internship(job_title, desc, stipend_text):
                    continue
            else:
                if not is_matching_job(job_title, desc):
                    continue

            success = apply_to_job(driver, job_url, job_title, applied_log)
            if success:
                applied += 1
                save_applied(CONFIG["log_file"], applied_log)
                time.sleep(CONFIG["action_delay"])

        except StaleElementReferenceException:
            continue
        except Exception as e:
            log.warning(f"  Skipping card: {e}")
            continue
    return applied

# ═══════════════════════════════════════════════════════════════
#  RUN AGENT
# ═══════════════════════════════════════════════════════════════
def run_agent():
    log.info("=" * 55)
    log.info(f"  Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 55)

    applied_log = load_applied(CONFIG["log_file"])
    log.info(f"Loaded {len(applied_log)} previously applied jobs")

    driver = create_driver()

    try:
        if not login(driver, CONFIG["email"], CONFIG["password"]):
            return

        # ── DAILY NAME UPDATE ─────────────────────────────────────
        log.info("\n" + "─" * 55)
        log.info("  DAILY NAME UPDATE")
        log.info("─" * 55)
        update_profile_name(driver)

        total_applied = 0
        loc = CONFIG["location"].lower()

        # ── SECTION 0: New Jobs & Internships (last 24 hrs) ───────
        log.info("\n" + "█" * 55)
        log.info("  SECTION 0 — New Jobs & Internships (Last 24 hrs)")
        log.info("█" * 55)

        for keyword in CONFIG["search_keywords"] + CONFIG["internship_keywords"]:
            slug = keyword.lower().replace(" ", "-")
            urls = [
                f"https://www.naukri.com/{slug}-jobs-in-{loc}?jobAge=1&experience=0",
                f"https://www.naukri.com/{slug}-jobs?jobAge=1&experience=0&wfhType=remote,hybrid",
            ]
            log.info(f"\n  New jobs keyword: {keyword}")
            for url in urls:
                cards = get_job_cards(driver, url)
                log.info(f"  Found {len(cards)} listings")
                n = process_job_cards(driver, cards, applied_log)
                total_applied += n

        # ── SECTION 1: Hyderabad Jobs ─────────────────────────────
        log.info("\n" + "█" * 55)
        log.info("  SECTION 1 — Hyderabad Jobs")
        log.info("█" * 55)

        for keyword in CONFIG["search_keywords"]:
            slug = keyword.lower().replace(" ", "-")
            url  = f"https://www.naukri.com/{slug}-jobs-in-{loc}?jobAge=1&experience=0"
            log.info(f"\n  Keyword: {keyword}")
            cards = get_job_cards(driver, url)
            log.info(f"  Found {len(cards)} listings")
            n = process_job_cards(driver, cards, applied_log)
            total_applied += n

        # ── SECTION 2: Hyderabad Internships ─────────────────────
        log.info("\n" + "█" * 55)
        log.info("  SECTION 2 — Hyderabad Internships")
        log.info("█" * 55)

        for keyword in CONFIG["internship_keywords"]:
            slug = keyword.lower().replace(" ", "-")
            urls = [
                f"https://www.naukri.com/internship/{slug}-internship-in-{loc}?jobAge=1",
                f"https://www.naukri.com/{slug}-internship-jobs-in-{loc}?jobtype=Internship&jobAge=1",
            ]
            log.info(f"\n  Keyword: {keyword}")
            for url in urls:
                cards = get_job_cards(driver, url)
                log.info(f"  Found {len(cards)} listings")
                n = process_job_cards(driver, cards, applied_log, is_internship=True)
                total_applied += n

        # ── SECTION 3: Remote/WFH Jobs ────────────────────────────
        log.info("\n" + "█" * 55)
        log.info("  SECTION 3 — Remote/WFH Jobs")
        log.info("█" * 55)

        for keyword in CONFIG["search_keywords"]:
            slug = keyword.lower().replace(" ", "-")
            url  = f"https://www.naukri.com/{slug}-jobs?jobAge=1&experience=0&wfhType=remote,hybrid"
            log.info(f"\n  Keyword: {keyword}")
            cards = get_job_cards(driver, url)
            log.info(f"  Found {len(cards)} listings")
            n = process_job_cards(driver, cards, applied_log)
            total_applied += n

        # ── SECTION 4: Remote/WFH Internships ────────────────────
        log.info("\n" + "█" * 55)
        log.info("  SECTION 4 — Remote/WFH Internships")
        log.info("█" * 55)

        for keyword in CONFIG["internship_keywords"]:
            slug = keyword.lower().replace(" ", "-")
            urls = [
                f"https://www.naukri.com/internship/{slug}-internship?wfhType=remote,hybrid&jobAge=1",
                f"https://www.naukri.com/{slug}-internship-jobs?jobtype=Internship&wfhType=remote,hybrid&jobAge=1",
            ]
            log.info(f"\n  Keyword: {keyword}")
            for url in urls:
                cards = get_job_cards(driver, url)
                log.info(f"  Found {len(cards)} listings")
                n = process_job_cards(driver, cards, applied_log, is_internship=True)
                total_applied += n

        log.info("\n" + "=" * 55)
        log.info(f"  Total applied this run: {total_applied}")
        log.info(f"  Total ever applied: {len(applied_log)}")
        log.info(f"  Run complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info("=" * 55)

    finally:
        driver.quit()

if __name__ == "__main__":
    run_agent()
