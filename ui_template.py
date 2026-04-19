# UI template separated from app.py for readability.

HTML_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>블로그 자동화</title>
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
    .preview-tabs {
      display: none;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .preview-tabs button.active {
      background: var(--ink);
      color: white;
      border-color: var(--ink);
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
      <h1>블로그 자동화</h1>
      <p class="subtitle">로컬 PC에서 계정 세션을 저장하고, 글 생성부터 티스토리 예약 업로드까지 실행합니다.</p>
    </div>
    <div class="header-actions">
      <button class="btn-dark" onclick="openModal('accountModal')">계정 추가</button>
      <button class="btn-green" onclick="openProjectModal()">프로젝트 등록</button>
      <button class="btn-ghost" onclick="openPromptModal()">프롬프트 관리</button>
    </div>
  </header>

  <section class="grid">
    <div class="card">
      <h2>프로젝트</h2>
      <label>프로젝트</label>
      <select id="projectSelect">
        <option value="">프로젝트를 선택하세요</option>
        {% for p in profiles %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
      </select>
      <div class="actions">
        <button class="btn-ghost" onclick="editProject()">선택 프로젝트 수정</button>
        <button class="btn-red" onclick="deleteProject()">선택 프로젝트 삭제</button>
      </div>
    </div>

    <div class="card">
      <h2>티스토리 계정</h2>
      <label>티스토리 계정</label>
      <select id="accountSelect">
        {% for a in accounts %}<option value="{{ a }}">{{ a }}</option>{% endfor %}
      </select>
      <div class="actions">
        <button class="btn-red" onclick="deleteAccount()">선택 계정 삭제</button>
      </div>
    </div>

    <div class="card wide">
      <h2>글쓰기 설정</h2>
      <label>추가 글 작성 형식</label>
      <select id="promptSelect">
        <option value="">기본 홍보형만 사용</option>
        {% for prompt in prompts %}
          {% if prompt != default_prompt_name %}<option value="{{ prompt }}">{{ prompt }}</option>{% endif %}
        {% endfor %}
      </select>
      <p class="hint">기본 홍보형은 항상 적용됩니다. 여기서 선택한 프롬프트는 추가 지침으로 덧붙습니다.</p>

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
      <div id="previewTabs" class="preview-tabs">
        <button class="btn-ghost" data-platform="naver" onclick="renderPreview('naver')">Naver</button>
        <button class="btn-ghost" data-platform="tistory" onclick="renderPreview('tistory')">Tistory</button>
        <button class="btn-ghost" data-platform="google" onclick="renderPreview('google')">Google</button>
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
    <p id="projectFetchStatus" class="hint">가져온 내용은 아래 프로젝트 상세 정보 칸에 채워집니다.</p>

    <div class="divider"></div>

    <label>프로젝트명</label>
    <input id="projectName" placeholder="예: XXX 공연 섭외">
    <label>프로젝트 상세 정보</label>
    <textarea id="projectInfo" placeholder="회사/프로젝트 소개, 강점, 서비스 범위"></textarea>
    <label>하단 고정 홍보문구</label>
    <textarea id="projectPromo" placeholder="기업 행사, 지역 축제, 대학 축제에 맞는 아티스트 섭외가 필요하다면 XX 공식 홈페이지에서 상담을 남겨주세요.
https://www.xxx.co.kr/"></textarea>
    <label>백링크 URL</label>
    <input id="projectBacklinkUrl" placeholder="https://www.example.com/">
    <label>앵커텍스트 후보 (줄바꿈으로 구분)</label>
    <textarea id="projectAnchorTexts" placeholder="예: 연예인 섭외 전문 위쇼&#10;가수 섭외 전문 에이전시&#10;여러개를 넣으면 그 중에서 선택해서 글을 작성합니다.(글 품질 향상)"></textarea>
    <div class="actions">
      <button class="btn-green" onclick="saveProject()">프로젝트 저장</button>
      <button class="btn-ghost" onclick="resetProjectForm()">새 프로젝트로 초기화</button>
    </div>
  </div>
</div>

<div id="promptModal" class="modal-backdrop" onclick="backdropClose(event)">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="promptModalTitle">
    <div class="modal-head">
      <h2 id="promptModalTitle">글 작성 프롬프트 관리</h2>
      <button class="modal-close" onclick="closeModal('promptModal')">닫기</button>
    </div>

    <label>기존 프롬프트 불러오기</label>
    <select id="promptManageSelect" onchange="loadPromptForEdit()">
      {% for prompt in prompts %}<option value="{{ prompt }}">{{ prompt }}</option>{% endfor %}
    </select>
    <p class="hint">프롬프트에는 {project_info}, {source_url}, {source_title}, {source_content}, {image_list}, {seo_keywords}, {youtube_url} 변수를 사용할 수 있습니다.</p>

    <label>프롬프트명</label>
    <input id="promptName" placeholder="예: 후기형_홍보글">
    <label>프롬프트 내용</label>
    <textarea id="promptContent" style="min-height: 360px" placeholder="블로그 글 작성 지침을 입력하세요."></textarea>

    <div class="actions">
      <button class="btn-green" onclick="savePrompt()">프롬프트 저장</button>
      <button class="btn-red" onclick="deletePrompt()">선택 프롬프트 삭제</button>
    </div>
  </div>
</div>

<script>
let currentJobId = null;
let latestPreviewData = null;
let currentPreviewPlatform = 'tistory';
let editingProjectFile = null;
const defaultPromptName = "{{ default_prompt_name }}";

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

async function openPromptModal() {
  openModal('promptModal');
  await loadPromptForEdit();
}

function refreshPromptSelects(prompts, selectedName) {
  const promptSelect = document.getElementById('promptSelect');
  if (promptSelect) {
    promptSelect.innerHTML = '';
    const baseOption = document.createElement('option');
    baseOption.value = '';
    baseOption.textContent = '기본 홍보형만 사용';
    baseOption.selected = !selectedName || selectedName === defaultPromptName;
    promptSelect.appendChild(baseOption);
    prompts.filter(prompt => prompt !== defaultPromptName).forEach(prompt => {
      const option = document.createElement('option');
      option.value = prompt;
      option.textContent = prompt;
      if (prompt === selectedName) option.selected = true;
      promptSelect.appendChild(option);
    });
  }

  const manageSelect = document.getElementById('promptManageSelect');
  if (manageSelect) {
    manageSelect.innerHTML = '';
    prompts.forEach(prompt => {
      const option = document.createElement('option');
      option.value = prompt;
      option.textContent = prompt;
      if (prompt === selectedName) option.selected = true;
      manageSelect.appendChild(option);
    });
  }
}

async function loadPromptForEdit() {
  const select = document.getElementById('promptManageSelect');
  const name = select.value;
  if (!name) return;
  const res = await fetch(`/get_prompt?name=${encodeURIComponent(name)}`);
  const data = await res.json();
  if (data.status === 'success') {
    document.getElementById('promptName').value = name;
    document.getElementById('promptContent').value = data.content || '';
  } else {
    alert(data.message || '프롬프트를 불러오지 못했습니다.');
  }
}

async function savePrompt() {
  const name = document.getElementById('promptName').value.trim();
  const content = document.getElementById('promptContent').value.trim();
  if (!name || !content) return alert('프롬프트명과 내용을 입력하세요.');

  const res = await fetch('/save_prompt', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, content})
  });
  const data = await res.json();
  if (data.status === 'success') {
    refreshPromptSelects(data.prompts || [], data.name);
    alert('프롬프트가 저장되었습니다.');
  } else {
    alert(data.message || '프롬프트 저장 실패');
  }
}

async function deletePrompt() {
  const name = document.getElementById('promptManageSelect').value;
  if (!name) return alert('삭제할 프롬프트를 선택하세요.');
  if (!confirm(`'${name}' 프롬프트를 삭제할까요?`)) return;

  const res = await fetch('/delete_prompt', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name})
  });
  const data = await res.json();
  if (data.status === 'success') {
    refreshPromptSelects(data.prompts || [], (data.prompts || [])[0]);
    await loadPromptForEdit();
    alert('프롬프트가 삭제되었습니다.');
  } else {
    alert(data.message || '프롬프트 삭제 실패');
  }
}

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

function extractUrls(text) {
  return Array.from(new Set((text || '').match(/https?:\\/\\/[^\\s<>"')]+/g) || []));
}

function getSection(content, sectionName) {
  const source = content || '';
  const marker = `### [${sectionName}] ###`;
  const start = source.indexOf(marker);
  if (start < 0) return '';
  const rest = source.slice(start + marker.length);
  const nextSection = rest.indexOf('### [');
  const section = nextSection >= 0 ? rest.slice(0, nextSection) : rest;
  return section.trim();
}

function getBacklinkUrl(backlinkSection) {
  const urls = extractUrls(backlinkSection);
  return urls[0] || '';
}

function getAnchorTexts(backlinkSection) {
  const match = (backlinkSection || '').match(/ANCHOR_TEXTS:\\s*([\\s\\S]*?)(?=\\n[A-Z_]+:|\\nRULE:|$)/);
  if (!match) return '';
  return match[1]
    .split('\\n')
    .map(line => line.replace(/^-\\s*/, '').trim())
    .filter(line => line && line !== '없음')
    .join('\\n');
}

function resetProjectForm() {
  editingProjectFile = null;
  document.getElementById('projectModalTitle').innerText = '프로젝트 등록 / URL 정보 가져오기';
  document.getElementById('projectUrl').value = '';
  document.getElementById('projectName').value = '';
  document.getElementById('projectInfo').value = '';
  document.getElementById('projectPromo').value = '';
  document.getElementById('projectBacklinkUrl').value = '';
  document.getElementById('projectAnchorTexts').value = '';
  document.getElementById('projectFetchStatus').innerText = '가져온 내용은 아래 프로젝트 상세 정보 칸에 채워집니다.';
}

function openProjectModal() {
  resetProjectForm();
  openModal('projectModal');
}

async function editProject() {
  try {
    const project = document.getElementById('projectSelect').value;
    if (!project) return alert('수정할 프로젝트를 선택하세요.');
    const res = await fetch(`/get_profile?name=${encodeURIComponent(project)}`, {cache: 'no-store'});
    if (!res.ok) throw new Error(`프로젝트 조회 실패: HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'success') return alert(data.message || '프로젝트를 불러오지 못했습니다.');

    const content = data.content || '';
    const backlinkSection = getSection(content, 'BACKLINK INFO');
    editingProjectFile = data.file;
    document.getElementById('projectModalTitle').innerText = '프로젝트 수정 / URL 정보 가져오기';
    document.getElementById('projectName').value = data.name || '';
    document.getElementById('projectInfo').value = getSection(content, 'PROJECT INFO') || content;
    document.getElementById('projectPromo').value = getSection(content, 'PROMO TEXT');
    document.getElementById('projectBacklinkUrl').value = getBacklinkUrl(backlinkSection);
    document.getElementById('projectAnchorTexts').value = getAnchorTexts(backlinkSection);
    document.getElementById('projectFetchStatus').innerText = '기존 프로젝트 정보를 불러왔습니다. 수정 후 저장하세요.';
    openModal('projectModal');
  } catch (error) {
    console.error(error);
    alert(`프로젝트 수정 화면을 열지 못했습니다. ${error.message || error}`);
  }
}

async function deleteProject() {
  const project = document.getElementById('projectSelect').value;
  if (!project) return alert('삭제할 프로젝트를 선택하세요.');
  if (!confirm(`'${project}' 프로젝트를 삭제할까요?`)) return;

  const res = await fetch('/delete_profile', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: project})
  });
  const data = await res.json();
  if (data.status === 'success') {
    alert('프로젝트가 삭제되었습니다.');
    location.reload();
  } else {
    alert(data.message || '프로젝트 삭제 실패');
  }
}

async function fetchProjectInfo() {
  const url = document.getElementById('projectUrl').value.trim();
  if (!url) return alert('URL을 입력하세요.');
  const status = document.getElementById('projectFetchStatus');
  status.innerText = 'URL 정보를 가져오는 중입니다...';
  const res = await fetch('/fetch_url_info', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url})
  });
  const data = await res.json();
  if (data.status === 'success') {
    document.getElementById('projectInfo').value = `[제목]\\n${data.title}\\n\\n[내용]\\n${data.content}`;
    const backlinkInput = document.getElementById('projectBacklinkUrl');
    if (backlinkInput && !backlinkInput.value.trim()) backlinkInput.value = url;
    status.innerText = data.source === 'gemini_report'
      ? 'Gemini로 프로젝트 보고서를 생성했습니다.'
      : 'Gemini 분석에 실패해 기본 스크래퍼 결과를 사용했습니다.';
  } else {
    status.innerText = 'URL 정보를 가져오지 못했습니다.';
    alert(data.message || 'URL 정보를 가져오지 못했습니다.');
  }
}

async function saveProject() {
  const name = document.getElementById('projectName').value.trim();
  const info = document.getElementById('projectInfo').value.trim();
  const promo = document.getElementById('projectPromo').value.trim();
  const backlinkUrl = document.getElementById('projectBacklinkUrl').value.trim();
  const anchorTexts = document.getElementById('projectAnchorTexts').value.trim();
  if (!name || !info) return alert('프로젝트명과 상세 정보를 입력하세요.');
  const backlinkUrls = Array.from(new Set([backlinkUrl, ...extractUrls(promo)].filter(Boolean)));
  const backlinkUrlLines = backlinkUrls.length
    ? backlinkUrls.map(url => `- ${url}`).join('\\n')
    : '없음';

  const content = [
    `### [PROJECT INFO] ###\\n${info}`,
    `### [PROMO TEXT] ###\\n${promo}`,
    `### [BACKLINK INFO] ###\\nURLS:\\n${backlinkUrlLines}\\nANCHOR_TEXTS:\\n${anchorTexts || '없음'}\\nRULE: URL을 단독 텍스트로 노출하지 말고 SEO 앵커텍스트 기반 하이퍼링크로 작성하세요. 하단 고정 홍보문구의 URL도 백링크 대상입니다.`
  ].join('\\n\\n');
  const res = await fetch('/save_profile', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, content, original: editingProjectFile})
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
    prompt: document.getElementById('promptSelect').value,
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
  fetchLatestPreview();
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
  const res = await fetch(`/get_latest_preview?ts=${Date.now()}`, {cache: 'no-store'});
  const data = await res.json();
  latestPreviewData = data;
  const hasPlatformPosts = data.posts && ['naver', 'tistory', 'google'].some(platform => {
    const post = data.posts[platform] || {};
    return post.title || post.content;
  });
  document.getElementById('previewTabs').style.display = hasPlatformPosts ? 'flex' : 'none';
  renderPreview(currentPreviewPlatform);
}

function renderPreview(platform) {
  currentPreviewPlatform = platform;
  const preview = document.getElementById('preview');
  preview.style.display = 'block';
  document.querySelectorAll('#previewTabs button').forEach(button => {
    button.classList.toggle('active', button.dataset.platform === platform);
  });
  if (!latestPreviewData) {
    preview.innerText = 'No preview loaded.';
    return;
  }
  const post = (latestPreviewData.posts || {})[platform] || {};
  const body = post.title || post.content
    ? `Title: ${post.title || ''}\\n\\n${post.content || ''}`
    : latestPreviewData.preview || '';
  preview.innerText = body || 'No preview result.';
}

function copyPreview() {
  const text = document.getElementById('preview').innerText;
  navigator.clipboard.writeText(text || '');
}
</script>
</body>
</html>
"""
