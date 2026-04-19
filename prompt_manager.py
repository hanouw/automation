from pathlib import Path


DEFAULT_PROMPT_NAME = "기본_홍보형"

DEFAULT_PROMPT_TEMPLATE = """당신은 대한민국 최고의 블로그 마케팅 전문가이자 SEO 전문가입니다.
아래 제공된 [참조 데이터]를 글의 핵심 주제로 삼고, [프로젝트 정보]는 브랜드 신뢰와 문의 유도에만 보조적으로 활용하여 최상의 블로그 포스팅을 작성해 주세요.

### 핵심 지침 (Instructions) ###
1. **주제 우선순위**: 글의 제목, 도입, 본문 전개, 핵심 정보는 반드시 [참조 데이터]를 기준으로 작성하세요. [프로젝트 정보]를 글의 메인 주제로 삼지 마세요.
2. **정보 비중**: [참조 데이터]를 본문 정보의 70~80% 이상으로 사용하고, [프로젝트 정보]는 20~30% 이하의 보조 홍보, 신뢰 요소, 문의 유도, 하단 고정 문구에만 사용하세요.
3. **내용 재구성**: [참조 데이터]의 내용을 그대로 베끼지 말고, 참조 링크의 인물/행사/상품/서비스가 글의 중심이 되도록 매력적으로 각색하세요.
4. **프로젝트 정보 사용 제한**: [프로젝트 정보]의 개요, 서비스 범위, 강점 보고서를 반복적으로 풀어 쓰지 마세요. 참조 데이터의 주제를 설명한 뒤 자연스럽게 프로젝트 서비스와 연결할 때만 사용하세요.
5. **SEO 최적화**: [SEO 핵심 문구]를 본문에 자연스럽게 녹여내세요 (3~5회 권장).
6. **백링크 삽입**: [프로젝트 정보]에 [BACKLINK INFO]가 있고 URL이 "없음"이 아니라면 각 플랫폼 본문에 백링크를 자연스럽게 1회 이상 포함하세요.
   - URL을 일반 텍스트로 노출하지 말고, ANCHOR_TEXTS 중 문맥에 맞는 앵커텍스트를 골라 하이퍼링크로 작성하세요.
   - 티스토리와 구글 본문은 <a href="URL" target="_blank" rel="noopener">앵커텍스트</a> 형식을 사용하세요.
   - 네이버 본문도 링크가 필요한 위치에는 <a href="URL" target="_blank" rel="noopener">앵커텍스트</a> 형식을 사용하세요.
   - [PROMO TEXT] 안에 URL이 있다면 해당 URL도 백링크 대상입니다. 마무리 문구에 URL을 그대로 쓰지 말고 하이퍼링크로 바꾸세요.
7. **이미지 배치**: [이미지 목록]에 있는 URL들을 본문 중간중간에 <img> 태그로 넣으세요. 이미지 앞 뒤로 한 줄씩 띄우세요.
   - **중요**: 각 <img> 태그에는 이미지의 시각적 내용과 [SEO 핵심 문구]를 결합한 'alt' 속성을 반드시 구체적으로 작성하세요.
   - **금지**: [이미지 목록]에 없는 이미지 URL은 절대 만들거나 추측하지 마세요.
   - **금지**: src 또는 alt에 logo, ico, icon, 아이콘, btn, common, header, footer, banner, nav, menu, sprite, sns가 들어가는 이미지는 절대 사용하지 마세요.
8. **유튜브 임베드**: [유튜브 URL]이 있다면 **반드시 본문 내용이 모두 끝난 뒤, 하단 고정 홍보문구 바로 위**에 <iframe> 형태의 티스토리 호환 임베드 코드를 삽입하세요.
9. **마무리**: 글의 마지막에는 반드시 [프로젝트 정보]의 '하단 고정 홍보문구'를 그대로 넣으세요.
10. **형식**: 티스토리는 HTML 형식, 네이버는 가독성 좋은 텍스트(이모지 포함) 형식으로 작성하세요.

### 입력 데이터 (Input Data) ###
[프로젝트 및 홍보 정보]
{project_info}

[참조 데이터 (URL 추출)]
- 원천: {source_url}
- 제목: {source_title}
- 내용: {source_content}

[이미지 목록]
{image_list}

[SEO 핵심 문구]
{seo_keywords}

[유튜브 URL]
{youtube_url}

### 출력 형식 (JSON) ###
반드시 아래 구조의 JSON으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{
  "naver": { "title": "네이버 제목", "content": "네이버 본문" },
  "tistory": { "title": "티스토리 제목", "content": "티스토리 HTML 본문" },
  "google": { "title": "SEO 제목", "content": "SEO 최적화 본문" }
}
"""


def safe_prompt_name(name):
    return "".join(c for c in (name or "") if c.isalnum() or c in (" ", "_", "-")).strip()


def prompt_path(prompt_dir, name):
    safe_name = safe_prompt_name(name)
    if not safe_name:
        return None
    return Path(prompt_dir) / f"{safe_name}.md"


def ensure_default_prompt(prompt_dir):
    prompt_dir = Path(prompt_dir)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    default_path = prompt_path(prompt_dir, DEFAULT_PROMPT_NAME)
    if default_path and not default_path.exists():
        default_path.write_text(DEFAULT_PROMPT_TEMPLATE, encoding="utf-8")


def list_prompts(prompt_dir):
    ensure_default_prompt(prompt_dir)
    prompts = []
    for path in sorted(Path(prompt_dir).glob("*.md")):
        prompts.append(path.stem)
    return prompts


def read_prompt(prompt_dir, name):
    ensure_default_prompt(prompt_dir)
    path = prompt_path(prompt_dir, name or DEFAULT_PROMPT_NAME)
    if not path or not path.exists():
        path = prompt_path(prompt_dir, DEFAULT_PROMPT_NAME)
    return path.read_text(encoding="utf-8")


def save_prompt(prompt_dir, name, content):
    ensure_default_prompt(prompt_dir)
    path = prompt_path(prompt_dir, name)
    if not path:
        raise ValueError("프롬프트명이 필요합니다.")
    if not content or not content.strip():
        raise ValueError("프롬프트 내용이 필요합니다.")
    path.write_text(content.strip(), encoding="utf-8")
    return path.stem


def delete_prompt(prompt_dir, name):
    ensure_default_prompt(prompt_dir)
    safe_name = safe_prompt_name(name)
    if not safe_name:
        raise ValueError("삭제할 프롬프트명이 필요합니다.")
    if safe_name == DEFAULT_PROMPT_NAME:
        raise ValueError("기본 프롬프트는 삭제할 수 없습니다.")

    path = prompt_path(prompt_dir, safe_name)
    if not path or not path.exists():
        raise FileNotFoundError("프롬프트 파일이 존재하지 않습니다.")
    path.unlink()
    return safe_name
