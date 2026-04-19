import json
import os
import time
from datetime import datetime
from glob import glob

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def get_env_var(key):
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    load_dotenv()
    return os.getenv(key)


def env_bool(key, default=False):
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    return raw_value.lower() in ("1", "true", "yes", "y", "on")


def accept_dialog_safely(dialog):
    message = dialog.message
    try:
        if "이어서 작성하시겠습니까" in message or "저장된 글" in message:
            dialog.dismiss()
            print(f"[*] Auto-dismissed saved draft dialog: {message}")
            return

        dialog.accept()
        print(f"[*] Auto-accepted dialog: {message}")
    except Exception as e:
        if "No dialog is showing" in str(e):
            return
        print(f"[WARN] Dialog already closed or could not be handled: {e}")


TISTORY_BLOG_NAME = get_env_var("TISTORY_BLOG_NAME")
TISTORY_ACCOUNT_NAME = os.getenv("TISTORY_ACCOUNT_NAME", "default")
ACCOUNT_ROOT_DIR = os.path.join(os.getcwd(), "tistory_user_data")
USER_DATA_DIR = os.path.join(ACCOUNT_ROOT_DIR, TISTORY_ACCOUNT_NAME)
STORAGE_STATE_PATH = os.path.join(USER_DATA_DIR, "storage_state.json")
HEADLESS_MODE = env_bool("HEADLESS_MODE", False)
ALLOW_INTERACTIVE_LOGIN = env_bool("ALLOW_INTERACTIVE_LOGIN", not HEADLESS_MODE)
USE_STORAGE_STATE = env_bool("TISTORY_USE_STORAGE_STATE", False)
UPLOAD_FILES_ENV = os.getenv("TISTORY_UPLOAD_FILES")

WRITE_READY_SELECTORS = [
    "#title-area",
    "input[name='title']",
    "textarea[name='title']",
    ".CodeMirror",
    "[contenteditable='true']",
]

KAKAO_LOGIN_SELECTORS = [
    "a.btn_login.link_kakao_id",
    "a.link_kakao_id",
    "a:has(.ico_kakao_type1)",
    "a:has(.txt_login)",
]

KAKAO_PROFILE_SELECTORS = [
    ".wrap_profile",
    "button:has(.thumb_profile)",
    "div:has(.thumb_profile)",
]


def wait_for_editor(page, timeout_ms=30000):
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        if "tistory.com/manage/newpost" in page.url.lower():
            return "url:manage/newpost"
        for selector in WRITE_READY_SELECTORS:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    return selector
            except Exception:
                pass
        time.sleep(1)
    return None


def dump_editor_debug(page, label="editor_not_ready"):
    debug_dir = os.path.join(os.getcwd(), "tistory_debug")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c for c in label if c.isalnum() or c in ("_", "-"))
    html_path = os.path.join(debug_dir, f"{timestamp}_{safe_label}.html")
    screenshot_path = os.path.join(debug_dir, f"{timestamp}_{safe_label}.png")

    try:
        title = page.title()
    except Exception as e:
        title = f"<title error: {e}>"

    try:
        body_text = page.locator("body").inner_text(timeout=2000)
    except Exception as e:
        body_text = f"<body text error: {e}>"

    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"[DEBUG] Saved page HTML: {html_path}")
    except Exception as e:
        print(f"[DEBUG] Could not save page HTML: {e}")

    try:
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"[DEBUG] Saved screenshot: {screenshot_path}")
    except Exception as e:
        print(f"[DEBUG] Could not save screenshot: {e}")

    print(f"[DEBUG] Page title: {title}")
    print(f"[DEBUG] Body text sample: {body_text[:500].replace(os.linesep, ' ')}")


def is_login_page(page):
    current_url = page.url.lower()
    if (
        "accounts.kakao.com" in current_url
        or "tistory.com/auth/login" in current_url
        or "tistory.com/member/find" in current_url
    ):
        return True

    login_form_selectors = [
        "input[name='loginId']",
        "input[name='password']",
    ]
    for selector in KAKAO_LOGIN_SELECTORS + login_form_selectors:
        try:
            if page.locator(selector).first.is_visible(timeout=500):
                return True
        except Exception:
            pass
    return False


def resolve_blog_id():
    config_path = os.path.join(USER_DATA_DIR, "config.json")
    blog_id = ""

    if TISTORY_BLOG_NAME:
        blog_id = TISTORY_BLOG_NAME.replace(".tistory.com", "")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        raw_url = config.get("blog_url", "").strip()
        clean_url = raw_url.replace("https://", "").replace("http://", "").replace("//", "").split("/")[0]
        if clean_url:
            blog_id = clean_url.split(".")[0]

    return blog_id


def click_first_visible(page, selectors, label):
    for selector in selectors:
        try:
            target = page.locator(selector).first
            if target.is_visible(timeout=1000):
                print(f"[*] Clicking {label}: {selector}")
                target.click(force=True)
                return True
        except Exception:
            pass
    return False


def open_tistory_login(page):
    page.goto("https://www.tistory.com/auth/login", wait_until="domcontentloaded")
    time.sleep(1)


def create_browser_context(playwright):
    args = ["--disable-blink-features=AutomationControlled"]
    context_options = {"accept_downloads": True}
    if HEADLESS_MODE:
        args.extend(["--no-sandbox", "--disable-dev-shm-usage"])
        context_options["viewport"] = {"width": 1440, "height": 1200}
    else:
        args.extend(["--start-maximized", "--window-size=1440,1200"])
        # In headed mode, make Playwright use the real browser window size.
        # A forced viewport can make the user-visible window look different
        # from the page geometry that Playwright is clicking.
        context_options["no_viewport"] = True

    if USE_STORAGE_STATE and os.path.exists(STORAGE_STATE_PATH):
        print(f"[*] Using storage_state: {STORAGE_STATE_PATH}")
        browser = playwright.chromium.launch(headless=HEADLESS_MODE, args=args)
        context = browser.new_context(
            storage_state=STORAGE_STATE_PATH,
            **context_options,
        )
        return browser, context

    print(f"[*] Using persistent profile: {USER_DATA_DIR}")
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=HEADLESS_MODE,
        args=args,
        **context_options,
    )
    return None, context


def get_or_create_page(context):
    for page in context.pages:
        if not page.is_closed():
            return page
    return context.new_page()


def dismiss_restore_popup(page):
    print("[*] Clearing editor popups if present...")
    # Tistory can show the saved-draft confirm a little after the editor URL is ready.
    # The dialog handler dismisses it; avoid sending random Enter/Arrow keys into the editor.
    time.sleep(2)


def ensure_writing_page(page, write_url):
    print(f"[*] Navigating to: {write_url}")
    page.goto(write_url, wait_until="domcontentloaded")

    ready_selector = wait_for_editor(page, timeout_ms=15000)
    if ready_selector:
        print(f"[+] Editor detected: {ready_selector}")
        return True

    if not is_login_page(page):
        print(f"[!] Editor not ready. Retrying write page. Current URL: {page.url}")
        page.goto(write_url, wait_until="domcontentloaded")
        ready_selector = wait_for_editor(page, timeout_ms=20000)
        if ready_selector:
            print(f"[+] Editor detected after retry: {ready_selector}")
            return True
        print(f"[-] Editor still not ready. Current URL: {page.url}")
        dump_editor_debug(page)
        return False

    if not ALLOW_INTERACTIVE_LOGIN:
        print("[-] Login page detected in non-interactive mode.")
        print(f"[-] Refresh account session first: {STORAGE_STATE_PATH}")
        return False

    print("[!] Login page detected. Trying interactive Kakao login...")
    if "tistory.com/member/find" in page.url.lower():
        print("[!] Tistory account-find page detected. Opening login page again.")
        open_tistory_login(page)

    if "tistory.com/auth/login" not in page.url.lower() and "accounts.kakao.com" not in page.url.lower():
        open_tistory_login(page)

    click_first_visible(page, KAKAO_LOGIN_SELECTORS, "Kakao login button")
    time.sleep(2)
    click_first_visible(page, KAKAO_PROFILE_SELECTORS, "saved Kakao profile")
    time.sleep(3)

    if "tistory.com/member/find" in page.url.lower():
        print("[!] Still on account-find page after login click. Returning to login page for manual action.")
        open_tistory_login(page)

    page.goto(write_url, wait_until="domcontentloaded")
    ready_selector = wait_for_editor(page, timeout_ms=30000)
    if ready_selector:
        print(f"[+] Login confirmed after opening editor: {ready_selector}")
        return True

    print("[*] Waiting for login completion. If a browser is open, complete login manually.")
    ready_selector = wait_for_editor(page, timeout_ms=120000)
    if ready_selector:
        print(f"[+] Login confirmed. Editor ready: {ready_selector}")
        return True

    print(f"[!] Editor not detected after login wait. Current URL: {page.url}")
    page.goto(write_url, wait_until="domcontentloaded")
    ready_selector = wait_for_editor(page, timeout_ms=30000)
    if ready_selector:
        print(f"[+] Editor detected after post-login retry: {ready_selector}")
        return True

    print("[!] Login seems incomplete.")
    dump_editor_debug(page, "login_incomplete")
    return False


def set_text_input(page, selectors, value):
    for selector in selectors:
        try:
            target = page.locator(selector).first
            if target.is_visible(timeout=1000):
                target.click()
                try:
                    target.fill(value)
                except Exception:
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    page.keyboard.insert_text(value)
                return True
        except Exception:
            pass
    return False


def set_title(page, title):
    success = set_text_input(
        page,
        ["#title-area", "input[name='title']", "textarea[name='title']"],
        title,
    )
    if not success and "tistory.com/manage/newpost" in page.url.lower():
        print("[!] Title area selector not found. Using focused editor fallback.")
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        page.keyboard.insert_text(title)
        success = True

    if not success:
        raise RuntimeError("Title area not found.")
    print(f"[+] Title set: {title[:20]}...")


def switch_to_html_mode(page):
    print("[*] Switching to HTML mode...")
    mode_selectors = [
        "#editor-mode-layer-btn-open",
        "button[id*='editor-mode']",
        "button[class*='editor-mode']",
    ]
    if not click_first_visible(page, mode_selectors, "editor mode button"):
        print("[!] Mode button not found. Proceeding with current editor mode.")
        return

    time.sleep(1)
    for _ in range(3):
        page.keyboard.press("ArrowDown")
        time.sleep(0.2)
    page.keyboard.press("Enter")
    time.sleep(0.2)
    page.keyboard.press("Enter")
    time.sleep(2)
    print("[+] HTML mode switch attempted.")


def set_codemirror_value(page, content):
    return page.evaluate(
        """
        (content) => {
            const editor = document.querySelector('.CodeMirror');
            if (!editor || !editor.CodeMirror) return false;
            const cm = editor.CodeMirror;
            cm.focus();

            // CodeMirror.setValue already fires CodeMirror's own change event.
            // Extra DOM input/change events can make Tistory duplicate the body.
            cm.setValue(content);
            cm.save();
            cm.refresh();
            cm.setCursor(cm.lineCount(), 0);
            const input = cm.getInputField();
            if (input) input.blur();
            return cm.getValue() === content;
        }
        """,
        content,
    )


def paste_codemirror_with_keyboard(page, content):
    def focus_editor_line():
        page.evaluate(
            """
            () => {
                const editor = document.querySelector('.CodeMirror');
                if (!editor || !editor.CodeMirror) return false;
                editor.scrollIntoView({block: 'center', inline: 'nearest'});
                editor.CodeMirror.focus();
                editor.CodeMirror.setCursor(0, 0);
                return true;
            }
            """
        )

        click_targets = [
            "pre.CodeMirror-line",
            ".CodeMirror-code pre",
            ".CodeMirror-line",
            ".CodeMirror-lines",
            ".CodeMirror-code",
        ]
        for selector in click_targets:
            try:
                target = page.locator(selector).first
                if target.is_visible(timeout=1000):
                    print(f"[*] Clicking CodeMirror input line: {selector}")
                    target.click(force=True, timeout=3000)
                    time.sleep(0.2)
                    break
            except Exception:
                pass

        page.evaluate(
            """
            () => {
                const editor = document.querySelector('.CodeMirror');
                if (editor && editor.CodeMirror) editor.CodeMirror.focus();
            }
            """
        )

    def get_codemirror_value():
        return page.evaluate(
            """
            () => {
                const editor = document.querySelector('.CodeMirror');
                if (!editor || !editor.CodeMirror) return null;
                return editor.CodeMirror.getValue();
            }
            """
        )

    page.evaluate(
        """
        () => {
            const editor = document.querySelector('.CodeMirror');
            if (!editor || !editor.CodeMirror) return;
            editor.scrollIntoView({block: 'center', inline: 'nearest'});
            editor.CodeMirror.focus();
            editor.CodeMirror.setCursor(0, 0);
        }
        """
    )
    focus_editor_line()
    time.sleep(0.3)
    page.keyboard.press("Control+a")
    page.keyboard.press("Backspace")
    time.sleep(0.3)

    previous_clipboard = None
    clipboard_was_read = False
    try:
        import pyperclip

        try:
            previous_clipboard = pyperclip.paste()
            clipboard_was_read = True
        except Exception:
            pass

        pyperclip.copy(content)
        focus_editor_line()
        page.keyboard.press("Control+V")
        time.sleep(0.8)

        if clipboard_was_read:
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                pass
    except Exception as e:
        print(f"[WARN] Clipboard paste failed. Falling back to keyboard insert: {e}")
        focus_editor_line()
        page.keyboard.insert_text(content)
        time.sleep(0.8)

    pasted_value = get_codemirror_value()
    if pasted_value != content:
        current_length = len(pasted_value or "")
        print(f"[WARN] Clipboard paste did not reach CodeMirror. length={current_length}; retrying with keyboard insert.")
        focus_editor_line()
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        time.sleep(0.2)
        page.keyboard.insert_text(content)
        time.sleep(1.0)

    page.evaluate(
        """
        () => {
            const editor = document.querySelector('.CodeMirror');
            if (!editor || !editor.CodeMirror) return;
            editor.CodeMirror.save();
            editor.CodeMirror.refresh();
            const input = editor.CodeMirror.getInputField();
            if (input) input.blur();
        }
        """
    )
    return True


def set_contenteditable_value(page, content):
    return page.evaluate(
        """
        (content) => {
            const target = document.querySelector('[contenteditable="true"]');
            if (!target) return false;
            target.focus();
            target.innerHTML = content;
            target.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertHTML', data: content}));
            target.dispatchEvent(new Event('change', {bubbles: true}));
            return true;
        }
        """,
        content,
    )


def verify_content_input(page, expected_content):
    try:
        result = page.evaluate(
            """
            (expected) => {
                const readValue = () => {
                    const editor = document.querySelector('.CodeMirror');
                    if (editor && editor.CodeMirror) {
                        return {source: 'CodeMirror', value: editor.CodeMirror.getValue()};
                    }
                    const editable = document.querySelector('[contenteditable="true"]');
                    if (editable) {
                        return {source: 'contenteditable', value: editable.innerHTML};
                    }
                    return {source: 'none', value: ''};
                };
                const current = readValue();
                const sampleLength = Math.min(120, expected.length, current.value.length);
                return {
                    source: current.source,
                    length: current.value.length,
                    expectedLength: expected.length,
                    prefixMatches: current.value.slice(0, sampleLength) === expected.slice(0, sampleLength),
                    exactMatches: current.value === expected,
                };
            }
            """,
            expected_content,
        )
        print(
            "[VERIFY] Editor content "
            f"source={result['source']} length={result['length']} "
            f"expected={result['expectedLength']} "
            f"prefixMatches={result['prefixMatches']} exactMatches={result['exactMatches']}"
        )
        if (
            not result["exactMatches"]
            and result["length"] == result["expectedLength"] * 2
            and result["prefixMatches"]
        ):
            print("[WARN] Editor content looks duplicated. Publish will be stopped for safety.")
        return result
    except Exception as e:
        print(f"[VERIFY] Content verification failed: {e}")
        return None

def paste_content(page, content):
    print("[*] Entering HTML content...")
    try:
        if page.locator(".CodeMirror").first.is_visible(timeout=1000):
            if not paste_codemirror_with_keyboard(page, content):
                raise RuntimeError("CodeMirror keyboard paste failed.")
            verification = verify_content_input(page, content)
            if not verification or not verification.get("exactMatches"):
                raise RuntimeError("CodeMirror content verification failed.")
            print("[+] Content pasted into CodeMirror via keyboard.")
            return True
    except Exception:
        raise

    try:
        if set_contenteditable_value(page, content):
            verification = verify_content_input(page, content)
            if verification and not verification.get("exactMatches"):
                raise RuntimeError("Contenteditable content verification failed.")
            print("[+] Content set via contenteditable API.")
            return True
    except Exception:
        pass

    for selector in [".CodeMirror-line", ".CodeMirror", "[contenteditable='true']"]:
        try:
            target = page.locator(selector).first
            if target.is_visible(timeout=1000):
                target.click()
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
                page.keyboard.insert_text(content)
                verification = verify_content_input(page, content)
                if verification and not verification.get("exactMatches"):
                    raise RuntimeError("Keyboard content verification failed.")
                print(f"[+] Content inserted via keyboard: {selector}")
                return True
        except Exception:
            pass

    raise RuntimeError("Content editor not found.")


def set_input_value(page, selectors, value):
    for selector in selectors:
        try:
            target = page.locator(selector).first
            if target.is_visible(timeout=1000):
                target.click()
                try:
                    target.fill(value)
                except Exception:
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    page.keyboard.insert_text(value)
                return True
        except Exception:
            pass
    return False


def parse_calendar_month(text):
    parts = "".join(char if char.isdigit() else " " for char in text).split()
    if len(parts) < 2:
        return None
    return int(parts[0]), int(parts[1])


def click_calendar_nav(page, direction):
    selector = f".layer_info button.btn_arr.btn_{direction}"
    try:
        button = page.locator(selector).first
        if button.is_visible(timeout=1000) and button.is_enabled():
            button.click(force=True)
            time.sleep(0.4)
            return True
    except Exception:
        pass
    return False


def click_calendar_day(page, day):
    buttons = page.locator(".layer_info .tbl_calendar button.btn_day")
    try:
        count = buttons.count()
        for index in range(count):
            button = buttons.nth(index)
            if button.inner_text(timeout=1000).strip() == str(day) and button.is_enabled():
                button.click(force=True)
                time.sleep(0.5)
                return True
    except Exception:
        pass
    return False


def get_reservation_state(page):
    try:
        return page.evaluate(
            """
            () => {
                const dateButton = document.querySelector('button.btn_reserve');
                const hourInput = document.querySelector('#dateHour, input[name="hour"], input[name="reserveHour"], input[id*="Hour"]');
                const minuteInput = document.querySelector('#dateMinute, input[name="minute"], input[name="reserveMinute"], input[id*="Minute"]');
                return {
                    date: dateButton ? dateButton.innerText.trim() : '',
                    hour: hourInput ? String(hourInput.value || '').padStart(2, '0') : '',
                    minute: minuteInput ? String(minuteInput.value || '').padStart(2, '0') : '',
                };
            }
            """
        )
    except Exception:
        return {"date": "", "hour": "", "minute": ""}


def set_reservation_date_with_calendar(page, target_date):
    target = datetime.strptime(target_date, "%Y-%m-%d")
    if not click_first_visible(page, ["button.btn_reserve"], "reservation date picker"):
        return False

    try:
        page.wait_for_selector(".layer_info .tbl_calendar button.btn_day", timeout=5000)
    except Exception:
        print("[!] Reservation calendar did not open.")
        return False

    target_month_index = target.year * 12 + target.month
    for _ in range(24):
        try:
            month_text = page.locator(".layer_info .txt_calendar").first.inner_text(timeout=2000)
        except Exception:
            print("[!] Reservation calendar month label not found.")
            return False

        current_month = parse_calendar_month(month_text)
        if not current_month:
            print(f"[!] Could not parse reservation calendar month: {month_text}")
            return False

        current_month_index = current_month[0] * 12 + current_month[1]
        if current_month_index == target_month_index:
            if click_calendar_day(page, target.day):
                state = get_reservation_state(page)
                if state.get("date") == target_date:
                    print(f"[+] Reservation date set to: {target_date}")
                    return True
                print(f"[!] Reservation date mismatch. expected={target_date}, actual={state.get('date')}")
                return False
            print(f"[!] Target day is not selectable in calendar: {target_date}")
            return False

        if current_month_index < target_month_index:
            if not click_calendar_nav(page, "next"):
                print(f"[!] Could not move reservation calendar forward to {target_date}.")
                return False
        else:
            if not click_calendar_nav(page, "prev"):
                print(f"[!] Could not move reservation calendar backward to {target_date}.")
                return False

    print(f"[!] Reservation calendar navigation limit reached. Target date was {target_date}")
    return False


def set_reservation_date(page, target_date):
    if not target_date:
        return False

    try:
        if set_reservation_date_with_calendar(page, target_date):
            return True
    except Exception as e:
        print(f"[!] Calendar date selection failed: {e}")

    success = set_input_value(
        page,
        [
            "input[type='date']",
            "#datePicker",
            "#datePickerInput",
            "#date",
            "input[name='date']",
            "input[name='reserveDate']",
            "input[id*='Date']",
            "input[class*='date']",
            "input[placeholder*='날짜']",
            "input[aria-label*='날짜']",
        ],
        target_date,
    )
    if not success:
        print(f"[!] Reservation date control not found. Target date was {target_date}")
        dump_editor_debug(page, "reservation_date_not_found")
    return success


def set_reservation_time(page, target_time):
    hour_val, minute_val = target_time.split(":")
    hour_val = hour_val.zfill(2)
    minute_val = minute_val.zfill(2)

    hour_success = set_input_value(
        page,
        [
            "#dateHour",
            "input[name='hour']",
            "input[name='reserveHour']",
            "input[id*='Hour']",
            "input[placeholder*='시']",
            "input[aria-label*='시']",
        ],
        hour_val,
    )
    minute_success = set_input_value(
        page,
        [
            "#dateMinute",
            "input[name='minute']",
            "input[name='reserveMinute']",
            "input[id*='Minute']",
            "input[placeholder*='분']",
            "input[aria-label*='분']",
        ],
        minute_val,
    )

    if not hour_success:
        print("[!] Hour input not found.")
    if not minute_success:
        print("[!] Minute input not found.")

    state = get_reservation_state(page)
    actual_time = f"{state.get('hour')}:{state.get('minute')}"
    expected_time = f"{hour_val}:{minute_val}"
    if actual_time != expected_time:
        print(f"[!] Reservation time mismatch. expected={expected_time}, actual={actual_time}")
        return False
    return hour_success and minute_success


def open_publish_panel(page):
    publish_openers = [
        "button#publish-layer-btn",
        "#publish-layer-btn",
    ]
    if click_first_visible(page, publish_openers, "publish opener"):
        try:
            page.wait_for_selector("#open20, input#open20, #publish-btn", timeout=5000)
        except Exception:
            pass
        time.sleep(1)
        return True
    print("[-] Publish opener not found: button#publish-layer-btn")
    return False


def configure_visibility_and_schedule(page, post_data):
    visibility_selectors = [
        "label[for='open20']",
        "input#open20",
        "label:has-text('공개')",
        "button:has-text('공개')",
    ]
    if click_first_visible(page, visibility_selectors, "public visibility"):
        print("[+] Visibility set to public.")
        time.sleep(0.8)
    else:
        print("[!] Public visibility control not found.")

    reserve_button_selectors = [
        "button:has-text('예약')",
        "label:has-text('예약')",
        "input[value='예약']",
        "button.btn_date",
        "button[class*='date']",
        "input[name='published']",
    ]
    if click_first_visible(page, reserve_button_selectors, "reservation option"):
        time.sleep(1)
        target_date = post_data.get("target_date")
        target_time = post_data.get("target_time", "19:00")
        print(f"[*] Target reservation: {target_date} {target_time}")
        date_success = set_reservation_date(page, target_date)
        time_success = set_reservation_time(page, target_time)
        state = get_reservation_state(page)
        actual_time = f"{state.get('hour')}:{state.get('minute')}"
        actual_date = state.get("date")
        if date_success and time_success:
            print(f"[+] Scheduled for: {actual_date} {actual_time}")
            return True

        print(
            "[WARN] Reservation schedule was not confirmed. "
            f"target={target_date} {target_time}, actual={actual_date} {actual_time}"
        )
        return False
    else:
        print("[!] Reservation control not found.")
        return False


def click_final_publish(page):
    final_publish_selectors = [
        "#publish-btn",
        "button#publish-btn",
        "button:has-text('발행')",
        "button:has-text('예약 발행')",
        "button:has-text('공개 발행')",
        "button.btn_publish",
        "button[class*='publish']",
    ]
    clicked = click_first_visible(page, final_publish_selectors, "final publish button")
    if clicked:
        time.sleep(3)
    return clicked


def get_upload_files(gen_dir):
    if UPLOAD_FILES_ENV:
        try:
            requested_files = json.loads(UPLOAD_FILES_ENV)
            files = []
            for file_path in requested_files:
                normalized = os.path.abspath(file_path)
                if os.path.exists(normalized) and normalized.endswith(".json"):
                    files.append(normalized)
                else:
                    print(f"[!] Requested upload file missing, skipped: {file_path}")
            return sorted(files, key=os.path.getctime)
        except Exception as e:
            print(f"[!] Invalid TISTORY_UPLOAD_FILES. Falling back to all files. error={e}")

    return sorted(glob(os.path.join(gen_dir, "*.json")), key=os.path.getctime)


def upload_tistory_blog():
    gen_dir = "text_generated"
    success_dir = os.path.join(gen_dir, "success")
    if not os.path.exists(success_dir):
        os.makedirs(success_dir)

    files = get_upload_files(gen_dir)
    if not files:
        print("[-] No JSON files found in text_generated/ folder.")
        return

    blog_id = resolve_blog_id()
    if not blog_id:
        print("[-] Blog ID could not be resolved. Check config.json or TISTORY_BLOG_NAME.")
        return

    print(f"[*] Found {len(files)} posts to upload.")

    browser = None
    context = None
    with sync_playwright() as p:
        print(f"[*] Launching Tistory browser... (Account: {TISTORY_ACCOUNT_NAME}, headless={HEADLESS_MODE})")
        browser, context = create_browser_context(p)
        page = get_or_create_page(context)
        page.on("dialog", accept_dialog_safely)

        try:
            for i, file_path in enumerate(files):
                print(f"\n[Post {i + 1}/{len(files)}] Processing: {os.path.basename(file_path)}")

                with open(file_path, "r", encoding="utf-8") as f:
                    post_data = json.load(f)

                if "tistory" not in post_data:
                    print(f"[-] Skip: No tistory data in {file_path}")
                    continue

                title = post_data["tistory"]["title"]
                content = post_data["tistory"]["content"]
                write_url = f"https://{blog_id}.tistory.com/manage/newpost/"
                print(
                    "[*] Loaded post target: "
                    f"{post_data.get('target_date')} {post_data.get('target_time', '19:00')}"
                )

                if not ensure_writing_page(page, write_url):
                    print("[-] Could not reach the Tistory editor. Skipping this post.")
                    continue

                print(f"[*] Editor URL confirmed: {page.url}")

                dismiss_restore_popup(page)

                print("[*] Entering title and content...")
                try:
                    set_title(page, title)
                    time.sleep(1)

                    switch_to_html_mode(page)
                    paste_content(page, content)
                    time.sleep(2)

                    print("[*] Finalizing publish settings...")
                    if not open_publish_panel(page):
                        raise RuntimeError("Publish panel could not be opened.")

                    if not configure_visibility_and_schedule(page, post_data):
                        raise RuntimeError("Reservation settings were not confirmed.")

                    print("[*] Clicking final publish button...")
                    if not click_final_publish(page):
                        raise RuntimeError("Final publish button not found.")

                    print(f"[SUCCESS] Post {i + 1} uploaded successfully!")
                    os.rename(file_path, os.path.join(success_dir, os.path.basename(file_path)))
                    time.sleep(5)

                except Exception as e:
                    print(f"[-] Execution error on post {i + 1}: {e}")
                    continue

            print("\n[*] All campaign uploads finished.")
        finally:
            if context:
                try:
                    context.storage_state(path=STORAGE_STATE_PATH)
                    print(f"[*] Refreshed storage_state: {STORAGE_STATE_PATH}")
                except Exception as e:
                    print(f"[!] Could not refresh storage_state: {e}")
                context.close()
            if browser:
                browser.close()


if __name__ == "__main__":
    upload_tistory_blog()
