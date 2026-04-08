import os
import json
import time
import pyperclip
import re
from glob import glob
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

TISTORY_BLOG_NAME = os.getenv("TISTORY_BLOG_NAME")
USER_DATA_DIR = os.path.join(os.getcwd(), "tistory_user_data")

def get_latest_post():
    """text_generated 폴더에서 가장 최신 JSON 파일을 읽어옵니다."""
    files = glob("text_generated/*.json")
    if not files:
        print("❌ 업로드할 JSON 파일이 없습니다.")
        return None
    latest_file = max(files, key=os.path.getctime)
    print(f"📄 최신 글 로드: {latest_file}")
    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)

def get_generated_images():
    """images_generated 폴더에서 이미지 파일들을 가져옵니다."""
    image_files = glob("images_generated/*.png") + glob("images_generated/*.jpg")
    image_files.sort(key=os.path.getctime, reverse=True)
    return image_files

def upload_tistory_blog():
    post_data = get_latest_post()
    if not post_data or "tistory" not in post_data:
        print("❌ 티스토리용 글 데이터가 없습니다.")
        return

    tistory_post = post_data["tistory"]
    title = tistory_post["title"]
    content = tistory_post["content"]

    image_paths = get_generated_images()
    blog_id = TISTORY_BLOG_NAME.replace(".tistory.com", "")

    with sync_playwright() as p:
        print(f"🚀 티스토리 브라우저 실행 중...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept()) 
        
        # 1. 글쓰기 페이지 접속
        write_url = f"https://{blog_id}.tistory.com/manage/newpost/"
        page.goto(write_url)
        
        # 2. 화면 인식 및 로그인 대기 (개선)
        print("⏳ 글쓰기 화면 진입을 확인 중입니다...")
        try:
            # 주소창에 newpost가 있거나 제목 필드가 보이면 성공
            page.wait_for_function(
                "() => window.location.href.includes('manage/newpost') || !!document.querySelector('#title-area') || !!document.querySelector('.tf_tit')",
                timeout=3000
            )
            print("✅ 글쓰기 화면 진입 성공!")
        except:
            try:
                # 카카오 로그인 버튼 클릭
                kakao_btn = page.locator("a:has-text('카카오계정으로 로그인')").first
                if kakao_btn.is_visible():
                    kakao_btn.click()
                    time.sleep(3)
                
                # 계정 선택: .wrap_profile 클릭
                print("👤 저장된 첫 번째 계정을 선택합니다.")
                account_profile = page.locator(".wrap_profile").first
                if account_profile.is_visible():
                    account_profile.click(force=True)
                    time.sleep(5)
                else:
                    # Tab 키로 이동 후 엔터 시도 (백업)
                    page.keyboard.press("Tab")
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(5)

                    print("✅ 로그인 확인되었습니다!")

            except Exception as e:
                print(f"⚠️ 자동 로그인 시도 중 오류: {e}")

        # 3. 팝업 제거 (안전하게)
        time.sleep(5) # 팝업 로딩 대기
        print("🧹 혹시 모를 팝업을 체크합니다...")
        # 팝업이 있을 때만 방향키 조작 (또는 무조건 실행 후 타이틀 클릭으로 상쇄)
        page.keyboard.press("ArrowRight")
        page.keyboard.press("Enter")
        time.sleep(2)

        # 4. 이미지 업로드 로직
        uploaded_image_tags = []
        if image_paths:
            print(f"📸 이미지 업로드를 시작합니다... (최신 2개 타겟)")
            for img_path in image_paths[:2]:
                try:
                    # '사진' 버튼을 찾아서 클릭하고 파일 선택
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        page.click("button[aria-label='사진'], .btn_image, #editor-mode-layer-btn-open + button", force=True)
                    file_chooser = fc_info.value
                    file_chooser.set_files(img_path)
                    print(f"✅ 이미지 전송: {os.path.basename(img_path)}")
                    time.sleep(5) 
                except Exception as e:
                    print(f"⚠️ 이미지 업로드 클릭 실패 (무시하고 계속): {e}")

            # HTML 모드로 전환하여 태그 추출
            print("🔄 HTML 모드로 전환 중...")
            try:
                page.click("#editor-mode-layer-btn-open")
                time.sleep(1)
                for _ in range(3): page.keyboard.press("ArrowDown"); time.sleep(0.2)
                page.keyboard.press("Enter")
                time.sleep(3)

                # 태그 추출
                html_content = page.locator(".CodeMirror-code").inner_text()
                image_tags = re.findall(r'(\[##_Image\|.*?_##\]|<img.*?>)', html_content)
                uploaded_image_tags = image_tags
                print(f"✅ 추출된 이미지 태그: {len(uploaded_image_tags)}개")

                # 에디터 비우기
                page.click(".CodeMirror-line")
                page.keyboard.press("Control+a")
                page.keyboard.press("Backspace")
            except:
                print("⚠️ HTML 모드 전환 중 오류가 발생했습니다.")
        else:
            # 이미지가 없을 때도 HTML 모드 전환은 필요함 (본문 주입을 위해)
            print("🔄 본문 입력을 위해 HTML 모드로 전환합니다.")
            page.click("#editor-mode-layer-btn-open")
            time.sleep(1)
            for _ in range(3): page.keyboard.press("ArrowDown"); time.sleep(0.2)
            page.keyboard.press("Enter")
            time.sleep(3)

        # 5. 본문 내용 치환 및 입력
        print("📝 본문 내용을 주입합니다...")
        final_content = content
        for i, tag in enumerate(uploaded_image_tags):
            placeholder = f"<!-- IMAGE_PLACEHOLDER_{i+1} -->"
            if placeholder in final_content:
                final_content = final_content.replace(placeholder, f"\n{tag}\n")
        
        pyperclip.copy(final_content)
        # HTML 에디터 영역 클릭 후 붙여넣기
        page.click(".CodeMirror-line", force=True)
        page.keyboard.press("Control+v")
        time.sleep(2)

        # 6. 제목 입력
        print("✏️ 제목 입력 중...")
        # 제목 칸을 찾기 위해 시도
        title_selectors = ["#title-area", ".tf_tit", "textarea.tf_tit"]
        for sel in title_selectors:
            try:
                if page.is_visible(sel):
                    page.click(sel)
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    pyperclip.copy(title)
                    page.keyboard.press("Control+v")
                    print("✅ 제목 입력 완료!")
                    break
            except: continue

        # 7. 발행
        print("🚀 발행 설정을 진행합니다...")
        complete_btn = page.locator("button:has-text('완료'), #publish-btn").first
        if complete_btn.is_visible():
            complete_btn.click()
            time.sleep(2)
            # 공개 설정 클릭 (label 또는 id 이용)
            try:
                page.click("label[for='open20']", force=True)
                time.sleep(1)
            except: pass
            
            final_btn = page.locator("#publish-btn").first
            if final_btn.is_visible():
                final_btn.click()
                print("🎊 모든 작업이 완벽하게 완료되었습니다!")
                time.sleep(5)

        context.close()

if __name__ == "__main__":
    upload_tistory_blog()
