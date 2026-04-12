from flask import Flask, render_template_string, request, jsonify
import os
import subprocess
import sys

app = Flask(__name__)

# 파일 저장 경로 설정
DATA_DIR = "source_data"
ACCOUNT_DIR = "tistory_user_data"
for d in [DATA_DIR, ACCOUNT_DIR]:
    if not os.path.exists(d): os.makedirs(d)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>블로그 자동화 에이전트 v2</title>
    <style>
        body { font-family: 'Pretendard', -apple-system, sans-serif; background: #f0f2f5; margin: 40px auto; max-width: 800px; padding: 20px; color: #333; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 25px; }
        h1 { text-align: center; color: #1a1a1a; margin-bottom: 30px; }
        h2 { color: #007bff; margin-top: 0; margin-bottom: 20px; font-size: 1.25rem; border-left: 5px solid #007bff; padding-left: 10px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; font-size: 0.95rem; }
        input, textarea, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; margin-bottom: 18px; font-size: 15px; }
        input:focus, textarea:focus, select:focus { border-color: #007bff; outline: none; box-shadow: 0 0 0 3px rgba(0,123,255,0.1); }
        .btn { background: #007bff; color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; transition: all 0.2s; font-size: 16px; }
        .btn:hover { background: #0056b3; transform: translateY(-1px); }
        .btn:active { transform: translateY(0); }
        .btn-save { background: #28a745; }
        .btn-save:hover { background: #218838; }
        .btn-secondary { background: #000000; width: auto; padding: 10px 15px; font-size: 14px; margin-bottom: 18px; }
        .status-box { padding: 20px; border-radius: 8px; display: none; margin-top: 20px; white-space: pre-wrap; font-size: 14px; line-height: 1.6; }
        .loading { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-left: 5px solid #ffc107; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-left: 5px solid #28a745; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-left: 5px solid #dc3545; }
        .flex-row { display: flex; gap: 10px; align-items: flex-start; }
        .flex-grow { flex-grow: 1; }
    </style>
</head>
<body>
    <h1>🤖 블로그 자동화 에이전트</h1>

    <!-- 1. 포스팅 실행 섹션 -->
    <div class="card">
        <h2>🚀 블로그 포스팅 실행</h2>
        
        <label>참조할 회사 프로필 선택</label>
        <select id="profileSelect">
            <option value="">-- 프로필을 선택하세요 --</option>
            {% for profile in profiles %}
            <option value="{{ profile }}">{{ profile }}</option>
            {% endfor %}
        </select>

        <label>사용할 티스토리 계정 선택</label>
        <div class="flex-row">
            <div class="flex-grow">
                <select id="accountSelect">
                    <option value="default">기본 계정 (Default)</option>
                    {% for acc in accounts %}
                    <option value="{{ acc }}">{{ acc }}</option>
                    {% endfor %}
                </select>
            </div>
            <button class="btn btn-secondary" onclick="addAccount()"> + 계정 추가</button>
        </div>

        <label>포스팅 주제/키워드 (비워두면 자유 생성)</label>
        <textarea id="postKeyword" style="height: 100px;" placeholder="오늘 포스팅할 주제를 구체적으로 입력하세요..."></textarea>
        
        <button id="runBtn" class="btn" onclick="runAutomation()">✨ 자동 포스팅 시작</button>
        <div id="status" class="status-box"></div>
    </div>

    <!-- 2. 회사 프로필 등록 섹션 -->
    <div class="card">
        <h2>🏢 회사 프로필 등록/관리</h2>
        <label>회사명 (예: Artsro, 김감자_수산물)</label>
        <input type="text" id="profileName" placeholder="회사나 서비스 이름을 입력하세요.">
        
        <label>회사 상세 내용 (URL, 특징, 핵심 키워드 등)</label>
        <textarea id="profileContent" style="height: 150px;" placeholder="회사의 주요 서비스와 특징을 상세히 입력하세요. Gemini가 이 내용을 학습합니다."></textarea>
        
        <button class="btn btn-save" onclick="saveProfile()">💾 프로필 저장하기</button>
    </div>

    <script>
        // 계정 추가 기능
        function addAccount() {
            const accName = prompt('새로운 계정 별칭을 입력하세요 (예: 개인블로그, 회사용):');
            if (accName && accName.trim()) {
                fetch('/add_account', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: accName.trim()})
                }).then(() => location.reload());
            }
        }

        // 프로필 저장 기능
        async function saveProfile() {
            const name = document.getElementById('profileName').value;
            const content = document.getElementById('profileContent').value;
            if(!name || !content) return alert('회사명과 내용을 모두 입력하세요.');

            try {
                const res = await fetch('/save_profile', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, content})
                });
                const data = await res.json();
                if(data.status === 'success') {
                    alert('프로필이 성공적으로 저장되었습니다.');
                    location.reload();
                } else {
                    alert('저장 중 오류가 발생했습니다.');
                }
            } catch(e) {
                alert('서버 통신 오류가 발생했습니다.');
            }
        }

        // 자동화 실행 기능
        async function runAutomation() {
            const profile = document.getElementById('profileSelect').value;
            const account = document.getElementById('accountSelect').value;
            const keyword = document.getElementById('postKeyword').value;
            const btn = document.getElementById('runBtn');
            const status = document.getElementById('status');

            if(!profile) return alert('회사를 선택해 주세요.');

            btn.disabled = true;
            btn.innerText = '⏳ 작업 진행 중...';
            status.style.display = 'block';
            status.className = 'status-box loading';
            status.innerText = 'AI가 글을 생성하고 티스토리에 접속 중입니다.\\n약 1~2분이 소요됩니다. 창을 닫지 마세요.';

            try {
                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({profile, keyword, account})
                });
                const result = await response.json();
                if(result.status === 'success') {
                    status.className = 'status-box success';
                    status.innerText = '✅ 모든 작업이 완료되었습니다!\\n선택하신 계정의 블로그를 확인해 보세요.';
                } else {
                    status.className = 'status-box error';
                    status.innerText = '❌ 오류 발생:\\n' + result.message;
                }
            } catch(e) {
                status.className = 'status-box error';
                status.innerText = '❌ 시스템 통신 오류가 발생했습니다.';
            } finally {
                btn.disabled = false;
                btn.innerText = '✨ 자동 포스팅 시작';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # 1. 프로필 목록 가져오기
    profiles = [f for f in os.listdir(DATA_DIR) if f.endswith('.md')]
    if 'product_info.md' in profiles: profiles.remove('product_info.md')
    profiles.sort()
    
    # 2. 계정 목록 가져오기
    accounts = [d for d in os.listdir(ACCOUNT_DIR) if os.path.isdir(os.path.join(ACCOUNT_DIR, d))]
    accounts.sort()
    
    return render_template_string(HTML_TEMPLATE, profiles=profiles, accounts=accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    data = request.json
    name = data.get('name', '').strip()
    if name:
        # 부모 폴더가 혹시 삭제되었을 경우를 대비해 다시 확인
        if not os.path.exists(ACCOUNT_DIR): os.makedirs(ACCOUNT_DIR)
        
        acc_path = os.path.abspath(os.path.join(ACCOUNT_DIR, name))
        if not os.path.exists(acc_path): os.makedirs(acc_path)
        
        # 🚀 계정 초기화를 위한 브라우저 실행 (수동 로그인 유도)
        python_exe = os.path.join("venv", "Scripts", "python.exe") if os.name == 'nt' else "python"
        if not os.path.exists(python_exe): python_exe = sys.executable

        # 일회성 로그인 스크립트 실행
        login_script = f"""
from playwright.sync_api import sync_playwright
import os
import time

with sync_playwright() as p:
    print("🔑 로그인 세션을 생성합니다...")
    context = p.chromium.launch_persistent_context(
        user_data_dir=r'{acc_path}',
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()
    page.goto('https://www.tistory.com/auth/login')
    
    print("📢 브라우저에서 로그인을 완료해주세요!")
    print("📢 로그인이 끝나고 티스토리 메인이나 글쓰기 화면이 나오면 브라우저를 닫으세요.")
    
    # 사용자가 브라우저를 직접 닫을 때까지 무한 대기
    while True:
        try:
            if not page.is_closed():
                time.sleep(1)
            else:
                break
        except:
            break
    context.close()
"""
        # 임시 스크립트 실행
        subprocess.Popen([python_exe, "-c", login_script])
        
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/save_profile', methods=['POST'])
def save_profile():
    data = request.json
    name = data.get('name', '').strip()
    content = data.get('content', '').strip()
    if name and content:
        # 파일명 정규화
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_', '-')]).strip()
        filename = f"{safe_name}.md"
        with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/run', methods=['POST'])
def run_automation():
    try:
        data = request.json
        profile_file = data.get('profile')
        account = data.get('account', 'default')
        keyword = data.get('keyword', '').strip()

        # 1. 회사 정보 읽기
        with open(os.path.join(DATA_DIR, profile_file), "r", encoding="utf-8") as f:
            profile_info = f.read()

        # 2. 컨텍스트 구성
        topic = keyword if keyword else "회사 정보를 바탕으로 홍보글을 자유롭게 작성해 주세요."
        merged_info = f"### [COMPANY INFO] ###\\n{profile_info}\\n\\n### [TODAY'S TOPIC] ###\\n{topic}"
        
        # 3. generator.py용 임시 파일 생성
        with open(os.path.join(DATA_DIR, "product_info.md"), "w", encoding="utf-8") as f:
            f.write(merged_info)

        # 4. run_all.py 실행 (환경 변수 전달)
        python_exe = os.path.join("venv", "Scripts", "python.exe") if os.name == 'nt' else "python"
        if not os.path.exists(python_exe): python_exe = sys.executable

        env = os.environ.copy()
        env["TISTORY_ACCOUNT_NAME"] = account

        # 작업 실행
        result = subprocess.run(
            [python_exe, "run_all.py"], 
            capture_output=True, 
            text=True, 
            encoding="utf-8", 
            env=env,
            errors="replace"
        )

        if result.returncode == 0:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": result.stderr or result.stdout})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    print("Flask Server starting at http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
