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

# 구글 세션 저장 폴더
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
    prompt = get_latest_image_prompt()
    if not prompt:
        print("❌ 이미지 프롬프트가 없습니다. generator.py를 먼저 실행하세요.")
        return

    # Gemini 웹용 명령어로 가공 (영문 프롬프트 앞에 'Create an image of' 추가)
    full_prompt = f"Generate 2 high-quality images of: {prompt}"

    with sync_playwright() as p:
        print(f"🚀 Gemini 웹 브라우저 실행 중... (세션 저장소: {USER_DATA_DIR})")
        
        # 자동화 탐지 방지를 위해 일반 브라우저처럼 위장
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            viewport={'width': 1280, 'height': 800}
        )
        
        page = context.new_page()
        
        # 1. Gemini 사이트 접속
        print("🌐 Gemini 웹사이트 접속 중...")
        page.goto("https://gemini.google.com/app")
        time.sleep(5)

        # 2. 로그인 확인 (로그인 버튼이 보이면 대기)
        if page.query_selector("text=로그인") or page.query_selector("text=Sign in"):
            print("🔑 구글 로그인이 필요합니다. 브라우저 창에서 로그인을 완료해 주세요!")
            print("⏳ 로그인이 완료되어 채팅창이 나타날 때까지 대기합니다...")
            # 채팅창(프롬프트 입력칸)이 보일 때까지 무한 대기
            page.wait_for_selector(".ql-editor, textarea, [contenteditable='true']", timeout=0)
            print("✅ 로그인 확인되었습니다!")
            time.sleep(3)

        # 3. 프롬프트 입력 및 전송
        print(f"📝 이미지 생성 요청 중: {prompt[:50]}...")
        
        try:
            # Gemini 입력창은 보통 contenteditable div입니다.
            input_selector = ".ql-editor, textarea, [contenteditable='true']"
            page.wait_for_selector(input_selector)
            
            # 사람처럼 타이핑 (또는 붙여넣기)
            page.click(input_selector)
            page.keyboard.type(full_prompt, delay=random.randint(20, 50))
            time.sleep(1)
            page.keyboard.press("Enter")
            
            print("⏳ 이미지가 생성되는 동안 기다립니다... (약 30초~1분)")
            
            # 4. 이미지 생성 완료 대기 (응답 완료를 알리는 요소 대기)
            # 이미지가 포함된 요소가 나타날 때까지 넉넉히 대기
            time.sleep(80) 
            
            # 5. 이미지 저장 로직
            # Gemini는 이미지 로딩이 완료되면 img 태그가 생성됩니다.
            # 가장 최신 응답의 이미지를 찾습니다.
            images = page.query_selector_all("img")
            
            output_dir = "images_generated"
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            
            count = 0
            for i, img in enumerate(images):
                src = img.get_attribute("src")
                # 구글에서 생성된 이미지는 보통 'https://...googleusercontent.com' 주소를 가짐
                if src and "googleusercontent.com" in src:
                    now = datetime.now().strftime("%m%d_%H%M")
                    img_path = os.path.join(output_dir, f"gemini_web_{now}_{count}.png")
                    
                    # 이미지를 스크린샷으로 찍거나 데이터 다운로드 (여기서는 간단히 로그 출력)
                    # 실제 운영 시에는 src 주소를 requests로 다운로드하는 로직 보강 가능
                    img.screenshot(path=img_path)
                    print(f"✅ 이미지 저장됨: {img_path}")
                    count += 1
                    if count >= 1: break # 첫 번째 이미지만 일단 저장
            
            if count == 0:
                print("⚠️ 생성된 이미지를 찾지 못했습니다. 수동 확인이 필요할 수 있습니다.")
                print("💡 생성은 완료되었을 수 있으니 브라우저 창을 확인해 보세요.")

        except Exception as e:
            print(f"❌ 작업 중 오류 발생: {e}")

        print("✅ 20초 후 브라우저를 종료합니다. (결과 확인용)")
        time.sleep(20)
        context.close()

if __name__ == "__main__":
    generate_image_on_web()
