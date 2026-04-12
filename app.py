from flask import Flask, render_template_string, request, jsonify
import os
import subprocess
import sys

app = Flask(__name__)

# 파일 저장 경로
DATA_DIR = "source_data"
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>블로그 자동화 에이전트 v2</title>
    <style>
        body { font-family: 'Pretendard', sans-serif; background: #f0f2f5; margin: 40px auto; max-width: 800px; padding: 20px; }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h1, h2 { color: #1a1a1a; margin-top: 0; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #444; }
        input, textarea, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; margin-bottom: 15px; font-size: 14px; }
        .btn { background: #007bff; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; transition: 0.3s; }
        .btn:hover { background: #0056b3; }
        .btn-save { background: #28a745; margin-top: 10px; }
        .btn-save:hover { background: #218838; }
        .status-box { padding: 15px; border-radius: 8px; display: none; margin-top: 15px; white-space: pre-wrap; font-size: 14px; }
        .loading { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        hr { border: 0; border-top: 1px solid #eee; margin: 25px 0; }
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
        
        <label>포스팅 주제/키워드 (오늘의 핵심 내용)</label>
        <textarea id="postKeyword" style="height: 100px;" placeholder="오늘 포스팅할 구체적인 주제나 이벤트를 입력하세요."></textarea>
        
        <button id="runBtn" class="btn" onclick="runAutomation()">✨ 자동 포스팅 시작</button>
        <div id="status" class="status-box"></div>
    </div>

    
    <!-- 2. 회사 프로필 등록 섹션 -->
    <div class="card">
        <h2>🏢 회사 프로필 등록/관리</h2>
        <label>회사명 (파일 이름)</label>
        <input type="text" id="profileName" placeholder="예: 김감자_수산물">
        <label>회사 상세 내용 (서비스 특징, URL 등)</label>
        <textarea id="profileContent" style="height: 120px;" placeholder="회사의 주요 서비스와 특징을 상세히 입력하세요."></textarea>
        <button class="btn btn-save" onclick="saveProfile()">💾 프로필 저장하기</button>
    </div>

    <script>
        // 프로필 저장
        async function saveProfile() {
            const name = document.getElementById('profileName').value;
            const content = document.getElementById('profileContent').value;
            if(!name || !content) return alert('회사명과 내용을 입력하세요.');

            const res = await fetch('/save_profile', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, content})
            });
            const data = await res.json();
            if(data.status === 'success') {
                alert('프로필이 저장되었습니다.');
                location.reload();
            }
        }

        // 자동화 실행
        async function runAutomation() {
            const profile = document.getElementById('profileSelect').value;
            const keyword = document.getElementById('postKeyword').value;
            const btn = document.getElementById('runBtn');
            const status = document.getElementById('status');

            if(!profile) return alert('회사를 선택해 주세요.');
            // keyword가 없어도 실행 가능하도록 체크 제거

            btn.disabled = true;
            btn.innerText = '⏳ 작업 중...';
            status.style.display = 'block';
            status.className = 'status-box loading';
            status.innerText = '글 생성 및 업로드를 진행 중입니다...';

            try {
                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({profile, keyword})
                });
                const result = await response.json();
                if(result.status === 'success') {
                    status.className = 'status-box success';
                    status.innerText = '✅ 완료! 블로그에 성공적으로 업로드되었습니다.';
                } else {
                    status.className = 'status-box error';
                    status.innerText = '❌ 오류: ' + result.message;
                }
            } catch(e) {
                status.className = 'status-box error';
                status.innerText = '❌ 시스템 통신 오류';
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
    # 저장된 md 파일 목록 가져오기
    profiles = [f for f in os.listdir(DATA_DIR) if f.endswith('.md')]
    # product_info.md는 리스트에서 제외 (내부용)
    if 'product_info.md' in profiles: profiles.remove('product_info.md')
    return render_template_string(HTML_TEMPLATE, profiles=profiles)

@app.route('/save_profile', methods=['POST'])
def save_profile():
    data = request.json
    name = data.get('name', '').strip()
    content = data.get('content', '').strip()
    if name and content:
        filename = f"{name}.md" if not name.endswith(".md") else name
        with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/run', methods=['POST'])
def run_automation():
    try:
        data = request.json
        profile_file = data.get('profile')
        keyword = data.get('keyword', '').strip()

        # 1. 회사 정보 읽기
        with open(os.path.join(DATA_DIR, profile_file), "r", encoding="utf-8") as f:
            profile_info = f.read()

        # 2. 컨텍스트 구성
        # 키워드가 비어있으면 자유 생성 지시문 삽입
        topic_instruction = keyword if keyword else "회사 정보를 바탕으로 흥미로운 블로그 홍보글을 자유롭게 작성해 주세요."
        
        merged_info = f"### [COMPANY INFO] ###\n{profile_info}\n\n### [TODAY'S TOPIC] ###\n{topic_instruction}"
        
        # 3. generator.py가 읽을 수 있도록 product_info.md에 저장
        with open(os.path.join(DATA_DIR, "product_info.md"), "w", encoding="utf-8") as f:
            f.write(merged_info)

        # 4. run_all.py 실행
        python_exe = os.path.join("venv", "Scripts", "python.exe") if os.name == 'nt' else "python"
        if not os.path.exists(python_exe): python_exe = sys.executable

        result = subprocess.run([python_exe, "run_all.py"], capture_output=True, text=True, encoding="utf-8")

        if result.returncode == 0:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": result.stderr or result.stdout})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000)
