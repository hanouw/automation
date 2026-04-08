import os
import json
import time
import random
from glob import glob
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

USER_DATA_DIR = os.path.join(os.getcwd(), "google_user_data")

def get_latest_image_prompt():
    """최신 JSON 파일에서 이미지 프롬프트를 읽어옵니다."""
    files = glob("text_generated/*.json")
    if not files: return None
    latest_file = max(files, key=os.path.getctime)
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("image_prompt")

def generate_image_on_web():
    now = datetime.now().strftime("%m%d_%H%M")
    prompt = get_latest_image_prompt()
    
    if not prompt:
        print("❌ 이미지 프롬프트가 없습니다.")
        return

    with sync_playwright() as p:
        print(f"🚀 Gemini 웹 브라우저 실행 중...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={'width': 1280, 'height': 900}
        )
        
        page = context.new_page()
        page.goto("https://gemini.google.com/app")
        time.sleep(5)

        try:
            # 1. '이미지 만들기' 클릭 및 템플릿 선택
            image_tool_btn = page.locator("button:has-text('이미지 만들기')").first
            if image_tool_btn.is_visible():
                image_tool_btn.click()
                time.sleep(3)
            
            page.wait_for_selector("media-gen-template-card", timeout=15000)
            templates = page.locator("media-gen-template-card").all()
            if templates:
                random.choice(templates).click()
                time.sleep(5)

            # 2. 프롬프트 입력
            print(f"📝 프롬프트 입력 및 전송 중...")
            input_selector = "div.ql-editor[contenteditable='true'], textarea"
            page.wait_for_selector(input_selector, timeout=20000)
            page.click(input_selector)
            page.keyboard.type(prompt, delay=30)
            page.keyboard.press("Enter")
            
            print("⏳ 이미지 생성 대기 중... (80초)")
            time.sleep(80) 

            # 3. 이미지 다운로드 로직 (강화됨)
            print("📸 이미지 다운로드를 시도합니다...")
            
            # 프로필 사진(.user-icon)을 제외하고, 실제 생성된 이미지만 찾습니다.
            # 보통 생성된 이미지는 'media-gen-result'나 특정 컨테이너 안에 있습니다.
            img_selector = "img[src*='googleusercontent.com']:not(.user-icon):not([alt*='프로필'])"
            
            try:
                # 이미지가 나타날 때까지 대기
                page.wait_for_selector(img_selector, timeout=30000)
                all_images = page.locator(img_selector).all()
                
                # 가장 마지막에 생성된 이미지를 선택
                target_img = all_images[-1]
                
                # 4. 다운로드 버튼 직접 클릭 (강제 클릭 모드)
                # 마우스 호버를 시도하되, 안 되어도 강제로 버튼을 찾아 클릭합니다.
                try:
                    target_img.hover(timeout=5000)
                    time.sleep(1)
                except:
                    pass

                download_btn_selector = "button[data-test-id='download-generated-image-button']"
                download_btn = page.locator(download_btn_selector).last # 가장 최근 버튼
                
                if download_btn:
                    print("✅ 다운로드 버튼 발견! 저장을 시작합니다... (최대 2분 대기)")
                    try:
                        # 다운로드 이벤트 대기 시간을 120초로 연장
                        with page.expect_download(timeout=120000) as download_info:
                            download_btn.click(force=True)
                        
                        download = download_info.value
                        output_dir = "images_generated"
                        if not os.path.exists(output_dir): os.makedirs(output_dir)
                        
                        save_path = os.path.join(output_dir, f"gemini_web_{now}.png")
                        download.save_as(save_path)
                        print(f"🎊 이미지 저장 완료: {save_path}")
                    except Exception as download_error:
                        print(f"⚠️ 다운로드 대기 시간 초과 또는 오류: {download_error}")
                        raise download_error
                else:
                    raise Exception("다운로드 버튼을 찾을 수 없습니다.")
            
            except Exception as inner_e:
                print(f"❌ 다운로드 중 오류: {inner_e}")
                print("💡 백업: 전체 화면 캡처를 시도합니다.")
                page.screenshot(path=os.path.join("images_generated", f"error_backup_{now}.png"))

        except Exception as e:
            print(f"❌ 전체 오류: {e}")

        print("✅ 10초 후 종료합니다.")
        time.sleep(10)
        context.close()

if __name__ == "__main__":
    generate_image_on_web()
