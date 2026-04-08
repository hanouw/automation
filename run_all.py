import subprocess
import sys
import os
import time

def run_script(script_name, description):
    """
    개별 파이썬 스크립트를 실행하는 헬퍼 함수
    """
    print(f"\n{'-'*50}")
    print(f"[START] {description}")
    print(f"{'-'*50}")
    
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    try:
        # PYTHONIOENCODING 환경변수를 utf-8로 설정하여 실행
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        process = subprocess.run(
            [python_exe, script_name], 
            check=True, 
            env=env,
            capture_output=False # 실시간 로그를 위해 False로 설정
        )
        print(f"\n[SUCCESS] {description} 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {description} 중 오류 발생 (Exit Code: {e.returncode})")
        return False

def main():
    print("AI Blog Automation System Start")
    start_time = time.time()

    # 1단계: 글 생성
    if not run_script("generator.py", "Step 1: Gemini Content Generation"):
        print("[STOP] Generation failed.")
        return

    time.sleep(2)

    # 2단계: 티스토리 업로드
    if not run_script("tistory_uploader.py", "Step 2: Tistory Auto Upload"):
        print("[STOP] Upload failed.")
        return

    end_time = time.time()
    print(f"\n{'-'*50}")
    print(f"All processes completed successfully!")
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"{'-'*50}")

if __name__ == "__main__":
    main()
