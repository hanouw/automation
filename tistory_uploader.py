import os
import json
import time
import pyperclip
import re
import sys
from glob import glob
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# 환경 변수 로드 (로컬: .env / 배포: st.secrets)
def get_env_var(key):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    load_dotenv()
    return os.getenv(key)

TISTORY_BLOG_NAME = get_env_var("TISTORY_BLOG_NAME")
USER_DATA_DIR = os.path.join(os.getcwd(), "tistory_user_data")

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

def upload_tistory_blog():
    post_data = get_latest_post()
    if not post_data or "tistory" not in post_data:
        print("❌ 티스토리용 글 데이터가 없습니다.")
        return

    tistory_post = post_data["tistory"]
    title = tistory_post["title"]
    content = tistory_post["content"]

    blog_id = TISTORY_BLOG_NAME.replace(".tistory.com", "")

    with sync_playwright() as p:
        # 1. 브라우저 실행 (세션 유지)
        print(f"🚀 티스토리 브라우저를 실행합니다... (세션 저장소: {USER_DATA_DIR})")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.new_page()
        
        # ⚠️ 브라우저 대화상자(Alert, Confirm) 자동 수락 설정
        page.on("dialog", lambda dialog: dialog.accept())
        
        # 2. 글쓰기 페이지 직접 이동
        print("🌐 티스토리 글쓰기 페이지 접속 중...")
        write_url = f"https://{blog_id}.tistory.com/manage/newpost/"
        page.goto(write_url)
        
        # 3. 화면 인식 및 로그인
        # 3. 화면 인식 및 로그인
        try:
            # 먼저 현재 페이지가 글쓰기 페이지인지 확인
            print("🔎 로그인 상태 확인 중...")
            page.wait_for_function(
                "() => window.location.href.includes('manage/newpost') || !!document.querySelector('#title-area')",
                timeout=5000  # 우선 5초만 대기해서 로그인 여부 판단
            )
            print("✅ 로그인 상태임이 확인되었습니다.")
        except:
            print("🔑 로그인이 필요합니다. 자동 로그인 시도 중...")
            try:
                # 카카오 로그인 버튼이 있으면 클릭
                kakao_btn = page.locator("a:has-text('카카오계정으로 로그인')").first
                if kakao_btn.is_visible():
                    kakao_btn.click()
                    time.sleep(2)
                
                # 저장된 계정(.wrap_profile)이 있는지 확인
                account_profile = page.locator(".wrap_profile").first
                if account_profile.is_visible():
                    print("👤 저장된 첫 번째 계정을 선택합니다.")
                    account_profile.click(force=True)
                else:
                    # ⭐ 핵심 수정 부분: 자동 선택이 불가능할 경우 수동 로그인 대기
                    print("📢 저장된 계정이 없습니다. 브라우저 창에서 직접 로그인을 완료해주세요!")
                    print("⏳ 로그인이 완료될 때까지 무한 대기합니다...")
                    
                    # 글쓰기 화면의 제목 입력 칸(#title-area)이 나타날 때까지 무한 대기 (timeout=0)
                    page.wait_for_selector("#title-area", timeout=0)
                    print("✅ 수동 로그인 확인! 계속 진행합니다.")

            except Exception as e:
                print(f"⚠️ 로그인 처리 중 오류 발생: {e}")
                print("⏳ 수동으로 글쓰기 화면까지 진입해주세요...")
                page.wait_for_selector("#title-area", timeout=0)
        # try:
        #     page.wait_for_function(
        #         "() => window.location.href.includes('manage/newpost') || !!document.querySelector('#title-area')",
        #         timeout=2000
        #     )
        #     print("✅ 글쓰기 화면 진입 확인!")
        # except:
        #     try:
        #         # 카카오 로그인 버튼 클릭
        #         kakao_btn = page.locator("a:has-text('카카오계정으로 로그인')").first
        #         if kakao_btn.is_visible():
        #             kakao_btn.click()
        #             time.sleep(3)
                
        #         # 계정 선택: .wrap_profile 클릭
        #         print("👤 저장된 첫 번째 계정을 선택합니다.")
        #         account_profile = page.locator(".wrap_profile").first
        #         if account_profile.is_visible():
        #             account_profile.click(force=True)
        #             time.sleep(5)
        #         else:
        #             # Tab 키로 이동 후 엔터 시도 (백업)
        #             page.keyboard.press("Tab")
        #             time.sleep(0.5)
        #             page.keyboard.press("Enter")
        #             time.sleep(5)
        #     except Exception as e:
        #         print(f"⚠️ 자동 로그인 시도 중 오류: {e}")

        # 4. 방해 요소 제거 (키보드 조작 방식)
        print("🧹 팝업을 확인하고 취소합니다...")
        time.sleep(3)
        # 오른쪽 방향키를 눌러 '취소' 버튼으로 포커스 이동 후 엔터
        page.keyboard.press("ArrowRight")
        time.sleep(0.5)
        page.keyboard.press("Enter")
        print("✅ 팝업 처리를 완료했습니다.")
        time.sleep(2)

        # 5. 글 작성
        print("📝 글 작성을 시작합니다...")
        
        try:
            # 1. 제목 입력 (로딩 즉시 제목 칸이므로 바로 붙여넣기)
            print("✏️ 제목 입력 중...")
            pyperclip.copy(title)
            page.keyboard.press("Control+v")
            time.sleep(1)
            
            # 2. HTML 모드로 전환 (방향키 조작 방식)
            print("🔄 HTML 모드로 전환 중...")
            mode_btn = page.locator("#editor-mode-layer-btn-open").first
            if mode_btn.is_visible():
                mode_btn.click()
                time.sleep(1)
                # 아래 방향키 3번 누르고 엔터 (HTML 선택)
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
                page.keyboard.press("Enter")
                time.sleep(0.2)
                page.keyboard.press("Enter")
                print("✅ HTML 모드 전환 완료!")
                time.sleep(3) 
            
            # 3. 본문 입력
            print("✏️ 본문(HTML) 입력 중...")
            # HTML 모드(CodeMirror) 영역 클릭하여 포커스 주기
            try:
                # 사용자가 제공한 클래스 .CodeMirror-line 을 타겟팅
                codemirror_area = page.locator(".CodeMirror-line").first
                if codemirror_area.is_visible():
                    codemirror_area.click()
                    time.sleep(1)
                    # 전체 선택 후 삭제 (혹시 모를 초기화)
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Backspace")
                    time.sleep(0.5)
                    # 클립보드 복사 후 붙여넣기
                    pyperclip.copy(content)
                    page.keyboard.press("Control+v")
                else:
                    # 백업 로직: Tab으로 이동 시도
                    page.keyboard.press("Tab")
                    pyperclip.copy(content)
                    page.keyboard.press("Control+v")
            except Exception as e:
                print(f"⚠️ 본문 입력 중 세부 오류 (무시하고 계속): {e}")
                pyperclip.copy(content)
                page.keyboard.press("Control+v")

            time.sleep(2)
            print("🎉 제목과 본문 입력 완료!")

            print("🚀 발행 설정을 시작합니다...")
            complete_btn = page.locator("button:has-text('완료'), #publish-btn").first
            if complete_btn.is_visible():
                complete_btn.click()
                time.sleep(2)
                
                # '공개' 설정 (id="open20")
                print("📢 '공개'로 설정 변경...")
                try:
                    page.click("label[for='open20']", force=True)
                    time.sleep(1)
                except: pass

                # 최종 발행 버튼
                print("🎊 최종 발행 버튼 클릭!")
                final_btn = page.locator("#publish-btn").first
                if final_btn.is_visible():
                    final_btn.click()
                    print("✅ 티스토리 포스팅 발행 완료!")
                    time.sleep(5)
                else:
                    page.locator("button:has-text('발행')").last.click()

        except Exception as e:
            print(f"❌ 오류 발생: {e}")

        print("✅ 10초 후 종료합니다.")
        time.sleep(10)
        context.close()

if __name__ == "__main__":
    upload_tistory_blog()
