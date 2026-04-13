from flask import Flask, render_template_string, request, jsonify
import os
import json
import subprocess
import sys

app = Flask(__name__)

# 경로 설정
DATA_DIR = "source_data"
ACCOUNT_DIR = "tistory_user_data"

def init_folders():
    for d in [DATA_DIR, ACCOUNT_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

init_folders()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>블로그 자동화 v2</title>
    <style>
        body { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; max-width: 800px; margin: 40px auto; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 25px; }
        h2 { color: #007bff; margin-top: 0; border-left: 5px solid #007bff; padding-left: 10px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; }
        /* 폰트 상속 명시 */
        input, textarea, select, button { 
            font-family: inherit; 
            font-size: 14px; 
            width: 100%; 
            padding: 12px; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            box-sizing: border-box; 
            margin-bottom: 15px; 
        }
        .btn { background: #007bff; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; }
        .btn:hover { background: #0056b3; }
        .btn-save { background: #28a745; }
        .btn-secondary { background: #000000; width: 70px; padding: 10px 15px; font-size: 14px; margin-bottom: 18px; }
        .status-box { padding: 15px; border-radius: 8px; display: none; margin-top: 15px; white-space: pre-wrap; }
        .loading { background: #fff3cd; color: #856404; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>🤖 블로그 자동화 에이전트</h1>

    <div class="card">
        <h2>🚀 포스팅 실행</h2>
        <label>프로젝트 선택</label>
        <select id="profileSelect">
            <option value="">-- 선택하세요 --</option>
            {% for p in profiles %} <option value="{{ p }}">{{ p }}</option> {% endfor %}
        </select>

        <label>티스토리 계정 선택</label>
        <div style="display: flex; gap: 10px;">
            <select id="accountSelect">
                <option value="default">기본 계정 (Default)</option>
                {% for a in accounts %} <option value="{{ a }}">{{ a }}</option> {% endfor %}
            </select>
            <button class="btn btn-secondary" onclick="addAccount()">계정추가</button>
        </div>

        <label>오늘의 키워드 (선택)</label>
        <textarea id="postKeyword" placeholder="비워두면 자유 생성"></textarea>
        
        <button id="runBtn" class="btn" onclick="runAutomation()">✨ 자동 포스팅 시작</button>
        <div id="status" class="status-box"></div>
    </div>

    <div class="card">
        <h2>🏢 프로젝트 등록</h2>
        <input type="text" id="profileName" placeholder="프로젝트명">
        <textarea id="profileContent" style="height: 100px;" placeholder="프로젝트 상세 정보"></textarea>
        <button class="btn btn-save" onclick="saveProfile()">💾 저장</button>
    </div>

    <script>
        async function addAccount() {
            const name = prompt('계정 별칭을 입력하세요 (예: 개인용):');
            if (!name) return;
            const url = prompt('블로그 도메인을 입력하세요 (예: id.tistory.com):');
            if (!url) return;

            const res = await fetch('/add_account', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, blog_url: url})
            });
            const data = await res.json();
            if(data.status === 'success') {
                alert('브라우저가 열리면 로그인을 완료하고 창을 닫으세요.');
                location.reload();
            }
        }

        async function saveProfile() {
            const name = document.getElementById('profileName').value;
            const content = document.getElementById('profileContent').value;
            if(!name || !content) return alert('내용을 입력하세요.');
            await fetch('/save_profile', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, content})
            });
            alert('저장되었습니다.');
            location.reload();
        }

        async function runAutomation() {
            const profile = document.getElementById('profileSelect').value;
            const account = document.getElementById('accountSelect').value;
            const keyword = document.getElementById('postKeyword').value;
            const btn = document.getElementById('runBtn');
            const status = document.getElementById('status');

            if(!profile) return alert('프로젝트를 선택하세요.');

            btn.disabled = true;
            status.style.display = 'block';
            status.className = 'status-box loading';
            status.innerText = '작업 중... 약 1~2분 소요됩니다.';

            try {
                const res = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({profile, account, keyword})
                });
                const result = await res.json();
                if(result.status === 'success') {
                    status.className = 'status-box success';
                    status.innerText = '✅ 완료되었습니다!';
                } else {
                    status.className = 'status-box error';
                    status.innerText = '❌ 오류: ' + result.message;
                }
            } catch(e) {
                status.className = 'status-box error';
                status.innerText = '❌ 통신 에러';
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    profiles = [f for f in os.listdir(DATA_DIR) if f.endswith('.md')]
    if 'product_info.md' in profiles: profiles.remove('product_info.md')
    accounts = [d for d in os.listdir(ACCOUNT_DIR) if os.path.isdir(os.path.join(ACCOUNT_DIR, d))]
    return render_template_string(HTML_TEMPLATE, profiles=profiles, accounts=accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    data = request.json
    name = data.get('name', '').strip()
    blog_url = data.get('blog_url', '').strip()
    if name and blog_url:
        acc_path = os.path.abspath(os.path.join(ACCOUNT_DIR, name))
        if not os.path.exists(acc_path): os.makedirs(acc_path)
        with open(os.path.join(acc_path, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"blog_url": blog_url}, f)
        
        # 브라우저 실행 로직
        python_exe = os.path.join("venv", "Scripts", "python.exe") if os.name == 'nt' else "python"
        if not os.path.exists(python_exe): python_exe = sys.executable
        login_script = f"""
from playwright.sync_api import sync_playwright
import time
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(user_data_dir=r'{acc_path}', headless=False)
    page = context.new_page()
    page.goto('https://www.tistory.com/auth/login')
    while True:
        try:
            if page.is_closed(): break
            time.sleep(1)
        except: break
    context.close()
"""
        subprocess.Popen([python_exe, "-c", login_script])
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/save_profile', methods=['POST'])
def save_profile():
    data = request.json
    name, content = data.get('name', ''), data.get('content', '')
    if name and content:
        with open(os.path.join(DATA_DIR, f"{name}.md"), "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/run', methods=['POST'])
def run_automation():
    try:
        data = request.json
        profile, account, keyword = data.get('profile'), data.get('account'), data.get('keyword', '')
        
        with open(os.path.join(DATA_DIR, profile), "r", encoding="utf-8") as f:
            p_info = f.read()
        
        topic = keyword if keyword.strip() else "회사 정보를 바탕으로 홍보글을 자유롭게 작성해 주세요."
        merged = f"### [INFO] ###\\n{p_info}\\n\\n### [TOPIC] ###\\n{topic}"
        
        with open(os.path.join(DATA_DIR, "product_info.md"), "w", encoding="utf-8") as f:
            f.write(merged)

        python_exe = os.path.join("venv", "Scripts", "python.exe") if os.name == 'nt' else "python"
        env = os.environ.copy()
        env["TISTORY_ACCOUNT_NAME"] = account
        
        result = subprocess.run([python_exe, "run_all.py"], capture_output=True, text=True, encoding="utf-8", env=env, errors="replace")
        
        if result.returncode == 0: return jsonify({"status": "success"})
        else: return jsonify({"status": "error", "message": result.stderr or result.stdout})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    # app.run(host='127.0.0.1', port=5000)
    app.run(host='0.0.0.0', port=5000)
