import os
import sys
import time

from playwright.sync_api import sync_playwright


LOGIN_URL = "https://www.tistory.com/auth/login"
READY_SELECTORS = [
    "#title-area",
    "input[name='title']",
    "textarea[name='title']",
    ".CodeMirror",
    "[contenteditable='true']",
]


def is_editor_ready(page):
    try:
        if "tistory.com/manage/newpost" in page.url.lower():
            return True
        for selector in READY_SELECTORS:
            if page.locator(selector).first.is_visible(timeout=300):
                return True
    except Exception:
        return False
    return False


def save_storage_state(context, storage_state_path, reason):
    try:
        context.storage_state(path=storage_state_path)
        print(f"[SUCCESS] Saved storage state ({reason}): {storage_state_path}")
    except Exception as e:
        print(f"[WARN] Could not save storage state ({reason}): {e}")


def apply_readable_zoom(page):
    try:
        page.evaluate("document.documentElement.style.zoom = '85%'")
    except Exception:
        pass


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: capture_tistory_session.py <account_name> <account_path> [blog_url]")

    account_name = sys.argv[1]
    account_path = sys.argv[2]
    storage_state_path = os.path.join(account_path, "storage_state.json")

    os.makedirs(account_path, exist_ok=True)

    with sync_playwright() as p:
        print(f"Opening Tistory login window for: {account_name}")
        context = p.chromium.launch_persistent_context(
            user_data_dir=account_path,
            headless=False,
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,900",
            ],
            viewport={"width": 1280, "height": 900},
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        apply_readable_zoom(page)

        print("No automatic login actions will be performed.")
        print("Please click Kakao login manually and complete login.")
        print("Close the browser window after login. The session will be saved then.")

        saved_after_editor = False
        while True:
            try:
                if page.is_closed():
                    break

                if not saved_after_editor and is_editor_ready(page):
                    save_storage_state(context, storage_state_path, "editor detected")
                    saved_after_editor = True

                time.sleep(1)
            except Exception:
                break

        save_storage_state(context, storage_state_path, "browser closed")
        context.close()


if __name__ == "__main__":
    main()
