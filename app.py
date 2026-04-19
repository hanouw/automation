import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request

from scraper import scrape_url


def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_base_dir()
os.chdir(BASE_DIR)

DATA_DIR = BASE_DIR / "source_data"
ACCOUNT_DIR = BASE_DIR / "tistory_user_data"
GEN_DIR = BASE_DIR / "text_generated"
DEBUG_DIR = BASE_DIR / "tistory_debug"

for folder in [DATA_DIR, ACCOUNT_DIR, GEN_DIR, DEBUG_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CANCELED_JOBS = set()
ACTIVE_PROCESSES = {}


HTML_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>블로그 자동화 로컬 앱</title>
  <style>
    :root {
      --bg: #f3efe7;
      --ink: #1f2933;
      --muted: #64748b;
      --card: #fffaf0;
      --line: #e4d8c3;
      --blue: #2563eb;
      --green: #15803d;
      --red: #dc2626;
      --black: #111827;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 10% 0%, rgba(37, 99, 235, .12), transparent 28%),
        radial-gradient(circle at 90% 8%, rgba(21, 128, 61, .12), transparent 30%),
        var(--bg);
      color: var(--ink);
      font-family: "Pretendard", "Noto Sans KR", sans-serif;
    }
    main { max-width: 1080px; margin: 36px auto; padding: 0 20px 48px; }
    header { margin-bottom: 24px; }
    h1 { font-size: 34px; margin: 0 0 8px; letter-spacing: -0.04em; }
    .subtitle { color: var(--muted); margin: 0; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .card {
      background: rgba(255, 250, 240, .92);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 18px 45px rgba(31, 41, 51, .08);
    }
    .wide { grid-column: 1 / -1; }
    h2 { font-size: 18px; margin: 0 0 16px; }
    label { display: block; font-weight: 700; font-size: 13px; margin: 12px 0 6px; }
    input, textarea, select, button {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px 12px;
      font: inherit;
      background: white;
    }
    textarea { resize: vertical; min-height: 92px; }
    button {
      border: 0;
      cursor: pointer;
      font-weight: 800;
      color: white;
      background: var(--blue);
      transition: transform .12s ease, opacity .12s ease;
    }
    button:hover { transform: translateY(-1px); }
    button:disabled { opacity: .55; cursor: not-allowed; transform: none; }
    .btn-green { background: var(--green); }
    .btn-red { background: var(--red); }
    .btn-dark { background: var(--black); }
    .btn-ghost { background: white; color: var(--blue); border: 1px solid var(--blue); }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .actions { display: flex; gap: 10px; margin-top: 16px; }
    .hint { color: var(--muted); font-size: 13px; line-height: 1.5; margin: 8px 0 0; }
    .header-bar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    .header-actions {
      display: flex;
      gap: 10px;
      min-width: 340px;
    }
    .header-actions button { white-space: nowrap; }
    #status {
      display: none;
      white-space: pre-wrap;
      background: #101820;
      color: #9dfcbd;
      min-height: 280px;
      max-height: 520px;
      overflow: auto;
      font-family: "Cascadia Mono", Consolas, monospace;
      font-size: 13px;
      border-radius: 14px;
      padding: 16px;
      margin-top: 14px;
    }
    #preview {
      display: none;
      background: white;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      max-height: 420px;
      overflow: auto;
      font-size: 14px;
      line-height: 1.65;
      white-space: pre-wrap;
    }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background: rgba(15, 23, 42, .56);
      backdrop-filter: blur(6px);
      z-index: 50;
    }
    .modal-backdrop.show { display: flex; }
    .modal {
      width: min(720px, 100%);
      max-height: 88vh;
      overflow: auto;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 22px;
      box-shadow: 0 28px 90px rgba(15, 23, 42, .32);
    }
    .modal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .modal-head h2 { margin: 0; }
    .modal-close {
      width: auto;
      padding: 8px 12px;
      background: var(--black);
      border-radius: 999px;
    }
    .divider {
      height: 1px;
      background: var(--line);
      margin: 18px 0;
    }
    @media (max-width: 820px) {
      .grid, .row { grid-template-columns: 1fr; }
      .header-bar { display: block; }
      .header-actions { min-width: 0; margin-top: 16px; flex-direction: column; }
      h1 { font-size: 28px; }
      .actions { flex-direction: column; }
    }
  </style>
</head>
<body>
<main>
  <header class="header-bar">
    <div>
      <h1>블로그 자동화 로컬 앱</h1>
      <p class="subtitle">로컬 PC에서 계정 세션을 저장하고, 글 생성부터 티스토리 예약 업로드까지 실행합니다.</p>
    </div>
    <div class="header-actions">
      <button class="btn-dark" onclick="openModal('accountModal')">계정 추가</button>
      <button class="btn-green" onclick="openModal('projectModal')">프로젝트 등록</button>
    </div>
  </header>

  <section class="grid">
    <div class="card">
      <h2>프로젝트와 계정</h2>
      <label>프로젝트</label>
      <select id="projectSelect">
        <option value="">프로젝트를 선택하세요</option>
        {% for p in profiles %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
      </select>

      <label>티스토리 계정</label>
      <select id="accountSelect">
        {% for a in accounts %}<option value="{{ a }}">{{ a }}</option>{% endfor %}
      </select>
      <div class="actions">
        <button class="btn-red" onclick="deleteAccount()">선택 계정 삭제</button>
      </div>
      <p class="hint">계정 추가와 프로젝트 등록은 상단 버튼에서 관리합니다.</p>
    </div>

    <div class="card wide">
      <h2>글쓰기 설정</h2>
      <label>참조 링크 목록</label>
      <textarea id="refLinks" placeholder="https://example.com/page1&#10;https://example.com/page2"></textarea>

      <div class="row">
        <div>
          <label>SEO 핵심 문구</label>
          <input id="seoKeywords" placeholder="공연 섭외, 행사 대행">
        </div>
        <div>
          <label>유튜브 영상 URL</label>
          <input id="youtubeUrl" placeholder="https://youtube.com/watch?v=...">
        </div>
      </div>

      <div class="row">
        <div>
          <label>예약 간격, 일 단위</label>
          <input id="postInterval" type="number" min="0" value="1">
        </div>
        <div>
          <label>예약 시간</label>
          <input id="postTime" type="time" value="19:00">
        </div>
      </div>

      <div class="actions">
        <button onclick="runAutomation('generate')">글 생성만 하기</button>
        <button class="btn-green" onclick="runAutomation('post')">글 생성 후 예약 업로드</button>
        <button id="cancelBtn" class="btn-red" style="display:none" onclick="cancelAutomation()">작업 중단</button>
      </div>
      <div id="status"></div>
    </div>

    <div class="card wide">
      <h2>생성 결과 미리보기</h2>
      <div class="actions">
        <button class="btn-ghost" onclick="fetchLatestPreview()">최근 결과 보기</button>
        <button class="btn-ghost" onclick="copyPreview()">본문 복사</button>
      </div>
      <div id="preview"></div>
    </div>
  </section>
</main>

<div id="accountModal" class="modal-backdrop" onclick="backdropClose(event)">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="accountModalTitle">
    <div class="modal-head">
      <h2 id="accountModalTitle">계정 추가 / 세션 저장</h2>
      <button class="modal-close" onclick="closeModal('accountModal')">닫기</button>
    </div>
    <label>계정 별칭</label>
    <input id="accountName" placeholder="예: hanouw">
    <label>티스토리 주소</label>
    <input id="accountBlogUrl" placeholder="https://hanouw.tistory.com/">
    <div class="actions">
      <button class="btn-dark" onclick="addAccount()">계정 추가 및 로그인</button>
    </div>
    <p class="hint">EXE 앱에서는 서버가 아니라 내 PC에 세션이 저장되므로 직접 로그인 방식이 가장 안정적입니다. 추가 후 목록은 자동으로 새로고침됩니다.</p>
  </div>
</div>

<div id="projectModal" class="modal-backdrop" onclick="backdropClose(event)">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="projectModalTitle">
    <div class="modal-head">
      <h2 id="projectModalTitle">프로젝트 등록 / URL 정보 가져오기</h2>
      <button class="modal-close" onclick="closeModal('projectModal')">닫기</button>
    </div>

    <label>홈페이지 URL</label>
    <input id="projectUrl" placeholder="https://example.com">
    <button class="btn-ghost" onclick="fetchProjectInfo()">URL 정보 가져오기</button>
    <p class="hint">가져온 내용은 아래 프로젝트 상세 정보 칸에 채워집니다.</p>

    <div class="divider"></div>

    <label>프로젝트명</label>
    <input id="projectName" placeholder="예: 아츠로 공연 섭외">
    <label>프로젝트 상세 정보</label>
    <textarea id="projectInfo" placeholder="회사/프로젝트 소개, 강점, 서비스 범위"></textarea>
    <label>하단 고정 홍보문구</label>
    <textarea id="projectPromo" placeholder="문의 링크, 대표 문구, CTA"></textarea>
    <button class="btn-green" onclick="saveProject()">프로젝트 저장</button>
  </div>
</div>

<script>
let currentJobId = null;

function openModal(id) {
  document.getElementById(id).classList.add('show');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

function backdropClose(event) {
  if (event.target.classList.contains('modal-backdrop')) {
    event.target.classList.remove('show');
  }
}

document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.show').forEach(modal => modal.classList.remove('show'));
  }
});

function logLine(text) {
  const status = document.getElementById('status');
  status.style.display = 'block';
  status.innerText += text;
  status.scrollTop = status.scrollHeight;
}

async function addAccount() {
  const name = document.getElementById('accountName').value.trim();
  const blog_url = document.getElementById('accountBlogUrl').value.trim();
  if (!name || !blog_url) return alert('계정 별칭과 티스토리 주소를 입력하세요.');

  const res = await fetch('/add_account', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, blog_url})
  });
  const data = await res.json();
  if (data.status === 'success') {
    alert('브라우저가 열립니다. 로그인 완료 후 창을 닫으면 세션이 저장됩니다. 계정 목록을 새로고침합니다.');
    location.reload();
  } else {
    alert(data.message || '계정 추가 실패');
  }
}

async function deleteAccount() {
  const select = document.getElementById('accountSelect');
  const name = select.value;
  if (!name) return alert('삭제할 계정을 선택하세요.');
  if (name === 'default') return alert('default 계정은 삭제할 수 없습니다.');
  if (!confirm(`'${name}' 계정을 삭제할까요? 저장된 로그인 세션도 함께 삭제됩니다.`)) return;

  const res = await fetch('/delete_account', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name})
  });
  const data = await res.json();
  if (data.status === 'success') {
    alert('계정이 삭제되었습니다.');
    location.reload();
  } else {
    alert(data.message || '계정 삭제 실패');
  }
}

async function fetchProjectInfo() {
  const url = document.getElementById('projectUrl').value.trim();
  if (!url) return alert('URL을 입력하세요.');
  const res = await fetch('/fetch_url_info', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url})
  });
  const data = await res.json();
  if (data.status === 'success') {
    document.getElementById('projectInfo').value = `[제목]\\n${data.title}\\n\\n[내용]\\n${data.content}`;
  } else {
    alert(data.message || 'URL 정보를 가져오지 못했습니다.');
  }
}

async function saveProject() {
  const name = document.getElementById('projectName').value.trim();
  const info = document.getElementById('projectInfo').value.trim();
  const promo = document.getElementById('projectPromo').value.trim();
  if (!name || !info) return alert('프로젝트명과 상세 정보를 입력하세요.');

  const content = `### [PROJECT INFO] ###\\n${info}\\n\\n### [PROMO TEXT] ###\\n${promo}`;
  const res = await fetch('/save_profile', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, content})
  });
  const data = await res.json();
  if (data.status === 'success') {
    alert('저장되었습니다.');
    location.reload();
  } else {
    alert(data.message || '저장 실패');
  }
}

async function runAutomation(mode) {
  const project = document.getElementById('projectSelect').value;
  const links = document.getElementById('refLinks').value.split('\\n').map(v => v.trim()).filter(Boolean);
  if (!project || links.length === 0) return alert('프로젝트와 링크를 확인하세요.');

  currentJobId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const status = document.getElementById('status');
  status.innerText = '[SYSTEM] 작업을 시작합니다.\\n';
  status.style.display = 'block';
  document.getElementById('cancelBtn').style.display = 'block';

  const payload = {
    job_id: currentJobId,
    mode,
    project,
    links,
    account: document.getElementById('accountSelect').value,
    seo: document.getElementById('seoKeywords').value,
    youtube: document.getElementById('youtubeUrl').value,
    interval: document.getElementById('postInterval').value,
    time: document.getElementById('postTime').value
  };

  const response = await fetch('/run_campaign', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    logLine(decoder.decode(value, {stream: true}).replaceAll('\\\\n', '\\n'));
  }
  document.getElementById('cancelBtn').style.display = 'none';
  if (mode === 'generate') fetchLatestPreview();
}

async function cancelAutomation() {
  if (!currentJobId) return;
  logLine('\\n[CANCEL] 중단 요청을 보냈습니다.\\n');
  await fetch('/cancel_campaign', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({job_id: currentJobId})
  });
}

async function fetchLatestPreview() {
  const res = await fetch('/get_latest_preview');
  const data = await res.json();
  const preview = document.getElementById('preview');
  preview.style.display = 'block';
  preview.innerText = data.preview || '미리볼 결과가 없습니다.';
}

function copyPreview() {
  const text = document.getElementById('preview').innerText;
  navigator.clipboard.writeText(text || '');
}
</script>
</body>
</html>
"""


def safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()


def python_worker_command(worker_name, *args):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--worker", worker_name, *map(str, args)]
    return [sys.executable, "-u", str(BASE_DIR / "app.py"), "--worker", worker_name, *map(str, args)]


def process_env(extra=None):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONWARNINGS"] = "ignore::FutureWarning"
    if extra:
        env.update(extra)
    return env


def stream_worker(job_id, worker_name, args=None, env=None):
    args = args or []
    if job_id in CANCELED_JOBS:
        yield "__RETURN_CODE__:130\n"
        return

    process = subprocess.Popen(
        python_worker_command(worker_name, *args),
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=process_env(env),
    )
    ACTIVE_PROCESSES[job_id] = process
    try:
        for line in process.stdout:
            if job_id in CANCELED_JOBS:
                process.terminate()
                yield "[CANCEL] 실행 중인 작업자 프로세스를 종료했습니다.\n"
                break
            yield line
        process.wait()
        yield f"__RETURN_CODE__:{process.returncode}\n"
    finally:
        ACTIVE_PROCESSES.pop(job_id, None)


def run_and_stream(job_id, worker_name, args=None, env=None):
    returncode = None
    for line in stream_worker(job_id, worker_name, args, env):
        if line.startswith("__RETURN_CODE__:"):
            returncode = int(line.split(":", 1)[1])
            continue
        yield line
    return returncode


@app.route("/")
def index():
    profiles = sorted(p.name for p in DATA_DIR.glob("*.md") if p.name != "product_info.md")
    accounts = sorted(p.name for p in ACCOUNT_DIR.iterdir() if p.is_dir())
    if not accounts:
        accounts = ["default"]
    return render_template_string(HTML_TEMPLATE, profiles=profiles, accounts=accounts)


@app.route("/run_campaign", methods=["POST"])
def run_campaign():
    data = request.json or {}
    job_id = data.get("job_id") or str(time.time())
    CANCELED_JOBS.discard(job_id)

    def generate_logs():
        try:
            links = data.get("links", [])
            mode = data.get("mode", "generate")
            project = data.get("project")
            generated_files = []
            known_files = set(glob(str(GEN_DIR / "*.json")))

            with open(DATA_DIR / project, "r", encoding="utf-8") as f:
                project_full_info = f.read()

            target_time = data.get("time") or "19:00"
            interval_days = int(data.get("interval", 1))
            yield "[Step 1] 글 생성을 시작합니다.\n"
            yield f"[*] 예약 기준: 간격 {interval_days}일, 시간 {target_time}\n"
            for i, url in enumerate(links):
                if job_id in CANCELED_JOBS:
                    yield "[CANCEL] 다음 링크 처리 전에 중단했습니다.\n"
                    return

                yield f"[*] {i + 1}/{len(links)} 링크 수집: {url}\n"
                scraped = scrape_url(url)
                if not scraped:
                    yield f"[!] 스크레이핑 실패, 건너뜀: {url}\n"
                    yield "[INFO] 이 단계에서는 Gemini를 호출하지 않았으므로 AI 토큰/할당량 소진 문제가 아닙니다.\n"
                    continue
                if scraped.get("source_url") != url:
                    yield f"[*] URL 보정: {scraped.get('source_url')}\n"

                post_date = (datetime.now() + timedelta(days=interval_days * i)).strftime("%Y-%m-%d")
                campaign_input = {
                    "project_info": project_full_info,
                    "scraped_data": scraped,
                    "seo_keywords": data.get("seo", ""),
                    "youtube_url": data.get("youtube", ""),
                    "target_date": post_date,
                    "target_time": target_time,
                }
                with open(DATA_DIR / "campaign_input.json", "w", encoding="utf-8") as f:
                    json.dump(campaign_input, f, ensure_ascii=False, indent=2)

                returncode = yield from run_and_stream(job_id, "generator")
                if returncode == 42:
                    yield "[CRITICAL] Gemini 일일 사용량/토큰 할당량 초과로 중단합니다. 내일 다시 시도하거나 API 플랜/키를 확인하세요.\n"
                    return
                if returncode == 43:
                    yield "[CRITICAL] Gemini 분당 요청 한도 또는 일시적 할당량 제한이 계속되어 중단합니다. 잠시 후 다시 시도하세요.\n"
                    return
                if returncode != 0:
                    yield f"[ERROR] 글 생성 실패. exit={returncode}\n"
                    continue

                new_files = sorted(set(glob(str(GEN_DIR / "*.json"))) - known_files, key=os.path.getctime)
                known_files.update(new_files)
                generated_files.extend(new_files)
                if not new_files:
                    yield "[ERROR] 글 생성 프로세스는 종료됐지만 새 JSON 파일이 없습니다. Gemini 응답 형식 또는 API 상태를 확인하세요.\n"
                yield f"[OK] {i + 1}번 글 생성 완료. 새 파일 {len(new_files)}개\n"

            if mode != "post":
                yield "\n[OK] 글 생성만 완료했습니다.\n"
                return

            if job_id in CANCELED_JOBS:
                yield "[CANCEL] 업로드 전에 중단했습니다.\n"
                return

            if not generated_files:
                yield "\n[SKIP] 생성된 글 파일이 없어 티스토리 업로드를 건너뜁니다.\n"
                return

            yield f"\n[Step 2] 티스토리 예약 업로드를 시작합니다. 대상 {len(generated_files)}개\n"
            returncode = yield from run_and_stream(
                job_id,
                "uploader",
                env={
                    "TISTORY_ACCOUNT_NAME": data.get("account", "default"),
                    "TISTORY_UPLOAD_FILES": json.dumps(generated_files, ensure_ascii=False),
                    "HEADLESS_MODE": "false",
                    "ALLOW_INTERACTIVE_LOGIN": "true",
                    "TISTORY_USE_STORAGE_STATE": "false",
                },
            )
            if returncode == 0:
                yield "\n[OK] 티스토리 업로드 프로세스가 종료되었습니다.\n"
            else:
                yield f"\n[ERROR] 티스토리 업로드 실패. exit={returncode}\n"
        except Exception as e:
            yield f"[SERVER ERROR] {e}\n"
        finally:
            CANCELED_JOBS.discard(job_id)

    return Response(generate_logs(), mimetype="text/plain")


@app.route("/cancel_campaign", methods=["POST"])
def cancel_campaign():
    job_id = (request.json or {}).get("job_id")
    if not job_id:
        return jsonify({"status": "error", "message": "job_id is required"})

    CANCELED_JOBS.add(job_id)
    process = ACTIVE_PROCESSES.get(job_id)
    if process and process.poll() is None:
        process.terminate()
    return jsonify({"status": "cancel_requested"})


@app.route("/add_account", methods=["POST"])
def add_account():
    data = request.json or {}
    name = safe_name(data.get("name", ""))
    blog_url = data.get("blog_url", "").strip()
    if not name or not blog_url:
        return jsonify({"status": "error", "message": "계정명과 블로그 주소가 필요합니다."})

    account_path = ACCOUNT_DIR / name
    account_path.mkdir(parents=True, exist_ok=True)
    with open(account_path / "config.json", "w", encoding="utf-8") as f:
        json.dump({"blog_url": blog_url}, f, ensure_ascii=False, indent=2)

    subprocess.Popen(
        python_worker_command("capture_session", name, str(account_path), blog_url),
        cwd=BASE_DIR,
        env=process_env({"HEADLESS_MODE": "false"}),
    )
    return jsonify({"status": "success", "account": name})


@app.route("/delete_account", methods=["POST"])
def delete_account():
    data = request.json or {}
    name = safe_name(data.get("name", ""))
    if not name:
        return jsonify({"status": "error", "message": "삭제할 계정명이 필요합니다."})
    if name == "default":
        return jsonify({"status": "error", "message": "default 계정은 삭제할 수 없습니다."})

    account_path = (ACCOUNT_DIR / name).resolve()
    account_root = ACCOUNT_DIR.resolve()

    try:
        account_path.relative_to(account_root)
    except ValueError:
        return jsonify({"status": "error", "message": "잘못된 계정 경로입니다."})

    if not account_path.exists() or not account_path.is_dir():
        return jsonify({"status": "error", "message": "계정 폴더가 존재하지 않습니다."})

    shutil.rmtree(account_path)
    return jsonify({"status": "success", "account": name})


@app.route("/save_profile", methods=["POST"])
def save_profile():
    data = request.json or {}
    name = safe_name(data.get("name", ""))
    content = data.get("content", "")
    if not name or not content:
        return jsonify({"status": "error", "message": "프로젝트명과 내용이 필요합니다."})
    with open(DATA_DIR / f"{name}.md", "w", encoding="utf-8") as f:
        f.write(content)
    return jsonify({"status": "success"})


@app.route("/fetch_url_info", methods=["POST"])
def fetch_url_info():
    url = (request.json or {}).get("url", "")
    result = scrape_url(url)
    if not result:
        return jsonify({"status": "error", "message": "수집 실패"})
    return jsonify({"status": "success", "title": result["title"], "content": result["content"][:1500]})


@app.route("/get_latest_preview")
def get_latest_preview():
    files = sorted(GEN_DIR.glob("*.json"), key=os.path.getctime, reverse=True)
    if not files:
        return jsonify({"preview": ""})
    try:
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        tistory = data.get("tistory", {})
        return jsonify({"preview": f"제목: {tistory.get('title', '')}\\n\\n{tistory.get('content', '')}"})
    except Exception:
        return jsonify({"preview": ""})


def worker_main(worker_name, args):
    os.chdir(BASE_DIR)
    if worker_name == "generator":
        from generator import generate_blog_posts, read_campaign_data, save_posts

        result = generate_blog_posts(read_campaign_data())
        if result:
            save_posts(result)
        return 0

    if worker_name == "uploader":
        from tistory_uploader import upload_tistory_blog

        upload_tistory_blog()
        return 0

    if worker_name == "capture_session":
        from capture_tistory_session import main as capture_main

        sys.argv = ["capture_tistory_session.py", *args]
        capture_main()
        return 0

    print(f"Unknown worker: {worker_name}")
    return 2


def open_browser_later(port):
    time.sleep(1)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    if "--worker" in sys.argv:
        index = sys.argv.index("--worker")
        worker_name = sys.argv[index + 1]
        worker_args = sys.argv[index + 2:]
        raise SystemExit(worker_main(worker_name, worker_args))

    port = int(os.getenv("APP_PORT", "5000"))
    if os.getenv("OPEN_BROWSER", "true").lower() in ("1", "true", "yes", "on"):
        threading.Thread(target=open_browser_later, args=(port,), daemon=True).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()