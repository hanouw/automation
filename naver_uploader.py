import os
import json
import time
import pyperclip
from glob import glob
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

NAVER_ID = os.getenv("NAVER_ID")
USER_DATA_DIR = os.path.join(os.getcwd(), "naver_user_data")

def get_latest_post():
    """text_generated 폴더에서 가장 최신 JSON 파일을 읽어옵니다."""
    files = glob("text_generated/*.json")
    if not files:
        print("❌ 업로드할 JSON 파일이 없습니다.")
        return None
    latest_file = max(files, key=os.path.getctime)
    print(f"📄 최신 파일 로드 중: {latest_file}")
    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)

def upload_naver_blog():
    post_data = get_latest_post()
    if not post_data or "naver" not in post_data:
        print("❌ 네이버 블로그용 글 데이터가 없습니다.")
        return

    naver_post = post_data["naver"]
    title = naver_post["title"]
    content = naver_post["content"]

    with sync_playwright() as p:
        # 1. 브라우저 실행 (세션 유지)
        print(f"🚀 브라우저를 실행합니다... (세션 저장소: {USER_DATA_DIR})")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.new_page()
        
        # 2. 로그인 상태 확인 (더 정확한 요소 기반)
        print("🌐 네이버 접속 중...")
        page.goto("https://www.naver.com")
        time.sleep(5) # 메인 페이지 로딩 대기

        # 로그인 여부 체크: 메일함이나 알림 아이콘이 있는지 확인 (로그인 시에만 나타남)
        is_logged_in = page.query_selector(".MyView-module__link_logout___S6VAb, .MyView-module__item_mail___K0r_D")
        
        if not is_logged_in:
            print("🔑 로그인이 필요해 보입니다. (로그인 요소가 발견되지 않음)")
            page.goto("https://nid.naver.com/nidlogin.login")
            print("⏳ 로그인을 완료하고 네이버 메인 화면이 뜰 때까지 대기합니다...")
            page.wait_for_url("https://www.naver.com*", timeout=0)
            print("✅ 로그인 확인되었습니다!")
            time.sleep(3)
        else:
            print("✅ 이미 로그인된 상태입니다. 세션을 재사용합니다.")

        # 3. 글쓰기 페이지 이동
        print(f"📝 블로그 글쓰기 페이지로 이동합니다...")
        page.goto("https://blog.naver.com/GoBlogWrite.naver")
        
        # 4. 에디터 프레임(#mainFrame) 대기 및 전환
        print("🖼️ 에디터 로딩 대기 중...")
        try:
            page.wait_for_selector("#mainFrame", timeout=30000)
            frame_element = page.query_selector("#mainFrame")
            frame = frame_element.content_frame()
            print("✅ 에디터 프레임 접속 성공!")
        except Exception as e:
            print(f"❌ 에디터 프레임 접근 실패: {e}")
            context.close()
            return

        # 5. 프레임 내부 로직 시작
        try:
            time.sleep(5) 
            
            # 팝업 및 방해 요소 제거
            print("🧹 팝업 및 방해 요소를 제거합니다...")
            for text in ["취소", "새로 작성", "닫기"]:
                try:
                    btn = frame.get_by_role("button", name=text)
                    if btn.is_visible():
                        btn.click()
                        print(f"✅ '{text}' 버튼을 클릭하여 팝업을 닫았습니다.")
                        time.sleep(1)
                except: pass

            # 6. 제목 입력
            print("✏️ 제목 입력 중...")
            # 제목 필드 후보들
            title_selector = ".se-documentTitle-input, .se-placeholder, .document_title, textarea.se-ff-nanumgothic"
            title_field = frame.wait_for_selector(title_selector, timeout=10000)
            title_field.click()
            time.sleep(1)
            
            # JS를 사용하여 안전하게 제목 영역 비움 (취소선 방지)
            frame.evaluate("""(selector) => {
                const el = document.querySelector(selector);
                if (el) {
                    el.innerText = '';
                    el.innerHTML = '';
                }
            }""", title_selector)
            time.sleep(1)
            
            # 클립보드 복사 후 붙여넣기
            pyperclip.copy(title)
            page.keyboard.press("Control+v")
            time.sleep(1)
            
            # 7. 본문 입력
            print("✏️ 본문 입력 중...")
            page.keyboard.press("Tab") # 본문 영역 이동
            time.sleep(1)
            
            # 본문 영역 초기화 및 서식 지우기
            body_selector = ".se-content, .se-main-container, .se-text-paragraph"
            frame.evaluate("""(selector) => {
                const el = document.querySelector(selector);
                if (el) { el.innerHTML = '<p><br></p>'; }
            }""", body_selector)
            time.sleep(1)
            
            # 서식 초기화 단축키 입력 (혹시 모를 취소선 등 방지)
            page.keyboard.press("Control+\\") # 서식 지우기 단축키
            time.sleep(0.5)
            
            # 클립보드 복사 후 붙여넣기
            pyperclip.copy(content)
            page.keyboard.press("Control+v")
            time.sleep(2)

            print("🎉 제목과 본문 입력 완료!")
            
            # 8. 발행 버튼 클릭
            print("🚀 발행 프로세스를 시작합니다...")
            publish_open_btn = frame.locator("button:has-text('발행')").first
            if publish_open_btn.is_visible():
                publish_open_btn.click()
                print("✅ 발행 옵션 창을 열었습니다.")
                time.sleep(3)
                
                final_publish_btn = frame.locator("button:has-text('발행')").last
                if final_publish_btn.is_visible():
                    final_publish_btn.click()
                    print("🎊 블로그 포스팅 발행이 완료되었습니다!")
                    time.sleep(5)
                else:
                    print("⚠️ 최종 발행 버튼을 찾지 못했습니다.")
            else:
                print("❌ 발행 버튼을 찾을 수 없습니다.")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")

        print("✅ 10초 후 종료합니다.")
        time.sleep(10)
        context.close()

if __name__ == "__main__":
    upload_naver_blog()
