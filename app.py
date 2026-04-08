import streamlit as st
import os
import json
import subprocess
from datetime import datetime

# Playwright 설치 확인 및 자동 설치 (배포 환경용)
try:
    import playwright
except ImportError:
    subprocess.run(["pip", "install", "playwright"])
    subprocess.run(["playwright", "install", "chromium"])

# 페이지 설정
st.set_page_config(page_title="블로그 자동화 시스템", page_icon="🤖", layout="wide")

# 사이드바 설정
st.sidebar.title("⚙️ 설정")
blog_id = st.sidebar.text_input("티스토리 블로그 ID", value=os.getenv("TISTORY_BLOG_NAME", ""))
st.sidebar.info("API 키는 .env 파일에서 관리됩니다.")

# 메인 화면
st.title("🤖 AI 블로그 자동 포스팅 시스템")
st.markdown("---")

# 1. 정보 입력 섹션
st.subheader("📝 1. 포스팅 정보 입력")
product_info = st.text_area(
    "포스팅할 상품이나 회사에 대한 상세 정보를 입력하세요.",
    placeholder="여기에 복사한 상세페이지 내용이나 회사 소개글을 넣어주세요.",
    height=300
)

# 2. 실행 섹션
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 포스팅 시작", use_container_width=True):
        if not product_info:
            st.warning("먼저 정보를 입력해 주세요!")
        else:
            # 1단계: 정보 저장
            with open("source_data/product_info.md", "w", encoding="utf-8") as f:
                f.write(product_info)
            st.success("✅ 정보가 저장되었습니다.")

            # 2단계: 스크립트 실행 (run_all.py 호출)
            st.info("🔄 글 생성 및 업로드를 시작합니다. 잠시만 기다려 주세요...")
            
            with st.spinner("작업 진행 중..."):
                try:
                    # 환경별 파이썬 실행 경로 자동 인식
                    if os.name == 'nt': # Windows
                        python_exe = os.path.join("venv", "Scripts", "python.exe")
                        if not os.path.exists(python_exe): python_exe = "python"
                    else: # Linux (Streamlit Cloud)
                        python_exe = "python"
                    
                    # 모든 출력을 가져오기 위해 capture_output=True 사용
                    result = subprocess.run(
                        [python_exe, "run_all.py"], 
                        capture_output=True, 
                        text=True, 
                        encoding="utf-8", 
                        errors="replace"
                    )
                    
                    # 실행 결과 상세 출력 (디버깅용)
                    if result.stdout:
                        st.info("실행 로그:")
                        st.code(result.stdout)
                    
                    if result.returncode == 0:
                        st.success("🎊 모든 작업이 성공적으로 완료되었습니다!")
                    else:
                        st.error(f"❌ 작업 중 오류가 발생했습니다. (Exit Code: {result.returncode})")
                        if result.stderr:
                            st.warning("상세 에러 내용:")
                            st.code(result.stderr)
                except Exception as e:
                    st.error(f"시스템 실행 오류: {e}")

with col2:
    if st.button("📄 최근 생성된 글 확인", use_container_width=True):
        files = [f for f in os.listdir("text_generated") if f.endswith(".json")]
        if files:
            latest_file = max([os.path.join("text_generated", f) for f in files], key=os.path.getctime)
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.write("**제목:**", data["tistory"]["title"])
                st.markdown("**본문 미리보기:**")
                st.text_area("Content", data["tistory"]["content"], height=300)
        else:
            st.info("아직 생성된 글이 없습니다.")

st.markdown("---")
st.caption("© 2026 블로그 자동화 프로젝트 - Powered by Gemini AI")
