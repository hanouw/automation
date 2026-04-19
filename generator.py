import os
import json
import re
import sys
import time
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

from prompt_manager import DEFAULT_PROMPT_TEMPLATE

# 1. 설정 및 로드
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

BAD_IMAGE_KEYWORDS = ['logo', 'ico', 'icon', '아이콘', 'btn', 'common', 'header', 'footer', 'banner', 'nav', 'menu', 'sprite', 'sns']

OUTPUT_FORMAT_RULE = """

### 시스템 고정 출력 규칙 ###
프로젝트 정보에 [BACKLINK INFO]가 있고 URL이 "없음"이 아니라면 각 플랫폼 본문에 백링크를 자연스럽게 1회 이상 포함하세요.
- URL을 일반 텍스트로 그대로 노출하지 말고, 제공된 ANCHOR_TEXTS 중 문맥에 맞는 앵커텍스트를 골라 하이퍼링크로 작성하세요.
- tistory와 google 본문은 <a href="URL" target="_blank" rel="noopener">앵커텍스트</a> 형식을 사용하세요.
- naver 본문도 링크가 필요한 위치에는 <a href="URL" target="_blank" rel="noopener">앵커텍스트</a> 형식을 사용하세요.
- [PROMO TEXT] 안에 URL이 있다면 해당 URL도 백링크 대상입니다. 마무리 문구에 URL을 그대로 쓰지 말고 하이퍼링크로 바꾸세요.

반드시 아래 구조의 JSON으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{
  "naver": { "title": "네이버 제목", "content": "네이버 본문" },
  "tistory": { "title": "티스토리 제목", "content": "티스토리 HTML 본문" },
  "google": { "title": "SEO 제목", "content": "SEO 최적화 본문" }
}
"""


def has_bad_image_keyword(text):
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in BAD_IMAGE_KEYWORDS)


def image_key(image_url):
    match = re.search(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?', image_url or "", re.IGNORECASE)
    if not match:
        return ""
    raw_url = match.group(0).lower()
    raw_url = re.sub(r'^https?://', '', raw_url)
    return raw_url.split('?', 1)[0]


def is_allowed_image_url(image_url, allowed_image_keys):
    key = image_key(image_url)
    if not key:
        return False
    return key in allowed_image_keys


def remove_bad_images_from_content(content, allowed_image_keys=None):
    if not content:
        return content
    allowed_image_keys = allowed_image_keys or set()

    def replace_img(match):
        tag = match.group(0)
        src_match = re.search(r'\bsrc=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        src = src_match.group(1) if src_match else ""
        if has_bad_image_keyword(tag):
            return ""
        if allowed_image_keys and not is_allowed_image_url(src, allowed_image_keys):
            return ""
        return tag

    content = re.sub(r'<img\b[^>]*>', replace_img, content, flags=re.IGNORECASE)

    def replace_bare_url(match):
        url = match.group(0)
        if has_bad_image_keyword(url):
            return ""
        if allowed_image_keys and not is_allowed_image_url(url, allowed_image_keys):
            return ""
        return url

    return re.sub(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?', replace_bare_url, content, flags=re.IGNORECASE)


def extract_section(text, section_name):
    pattern = rf"### \[{re.escape(section_name)}\] ###\s*(.*?)(?=\n### \[|\Z)"
    match = re.search(pattern, text or "", re.DOTALL)
    return match.group(1).strip() if match else ""


def unique_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        value = (value or "").strip()
        if not value or value in seen or value == "없음":
            continue
        seen.add(value)
        result.append(value)
    return result


def extract_backlink_info(project_info):
    backlink_section = extract_section(project_info, "BACKLINK INFO")
    promo_section = extract_section(project_info, "PROMO TEXT")
    urls = []
    anchors = []

    if backlink_section:
        urls.extend(re.findall(r'https?://[^\s<>"\')]+', backlink_section))
        anchor_match = re.search(r'ANCHOR_TEXTS:\s*(.*?)(?=\n[A-Z_]+:|\Z)', backlink_section, re.DOTALL)
        if anchor_match:
            anchors.extend(line.strip("- ").strip() for line in anchor_match.group(1).splitlines())

    urls.extend(re.findall(r'https?://[^\s<>"\')]+', promo_section))
    return {
        "urls": unique_preserve_order(urls),
        "anchors": unique_preserve_order(anchors),
    }


def convert_bare_backlinks(content, backlink_info):
    if not content:
        return content
    urls = backlink_info.get("urls") or []
    anchors = backlink_info.get("anchors") or []
    if not urls:
        return content

    def is_attribute_value(text, start):
        prefix = text[max(0, start - 12):start].lower()
        return any(marker in prefix for marker in ('href="', "href='", 'src="', "src='"))

    def is_inside_anchor(text, start):
        last_open = text.lower().rfind("<a ", 0, start)
        last_close = text.lower().rfind("</a>", 0, start)
        return last_open > last_close

    for index, url in enumerate(urls):
        anchor = anchors[index % len(anchors)] if anchors else "자세히 보기"
        link = f'<a href="{url}" target="_blank" rel="noopener">{anchor}</a>'

        def replace(match):
            if is_attribute_value(content, match.start()) or is_inside_anchor(content, match.start()):
                return match.group(0)
            return link

        content = re.sub(re.escape(url), replace, content)
    if not any(f'href="{url}"' in content or f"href='{url}'" in content for url in urls):
        anchor = anchors[0] if anchors else "자세히 보기"
        content = f'{content}\n\n<p><a href="{urls[0]}" target="_blank" rel="noopener">{anchor}</a></p>'
    return content


def sanitize_posts(posts, allowed_images=None, project_info=""):
    if not isinstance(posts, dict):
        return posts
    allowed_image_keys = {image_key(url) for url in (allowed_images or [])}
    allowed_image_keys.discard("")
    backlink_info = extract_backlink_info(project_info)

    for channel in ("naver", "tistory", "google"):
        section = posts.get(channel)
        if isinstance(section, dict):
            content = remove_bad_images_from_content(section.get("content", ""), allowed_image_keys)
            section["content"] = convert_bare_backlinks(content, backlink_info)
    return posts


def read_campaign_data():
    """app.py에서 전달한 캠페인 데이터를 읽어옵니다."""
    file_path = "source_data/campaign_input.json"
    if not os.path.exists(file_path):
        print("ERROR: Campaign data file not found.")
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_prompt_template(template, values):
    rendered = template or DEFAULT_PROMPT_TEMPLATE
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value or ""))
    return rendered + OUTPUT_FORMAT_RULE


def wrap_project_info(project_info):
    return f"""아래 프로젝트 정보는 글의 메인 주제가 아니라 보조 홍보 자료입니다.
반드시 참조 데이터의 주제를 먼저 설명하고, 프로젝트 정보는 브랜드 신뢰, 서비스 연결, 문의 유도, 하단 고정 문구에만 제한적으로 사용하세요.
프로젝트 보고서의 개요/서비스 범위/강점을 글의 중심 내용으로 반복하지 마세요.

{project_info}
"""


def generate_blog_posts(data, max_retries=3):
    """Gemini API를 사용하여 포스팅을 생성합니다. (429 에러 시 재시도 로직 포함)"""
    if not data: return None
    
    project_info = data.get("project_info", "")
    scraped = data.get("scraped_data", {})
    seo_keywords = data.get("seo_keywords", "")
    youtube_url = data.get("youtube_url", "")
    prompt_template = data.get("prompt_template") or DEFAULT_PROMPT_TEMPLATE
    
    image_list_str = "\n".join([f"- {url}" for url in scraped.get("images", [])])

    prompt = render_prompt_template(
        prompt_template,
        {
            "project_info": wrap_project_info(project_info),
            "source_url": scraped.get("source_url"),
            "source_title": scraped.get("title"),
            "source_content": scraped.get("content"),
            "image_list": image_list_str,
            "seo_keywords": seo_keywords,
            "youtube_url": youtube_url,
        },
    )
    
    print(f"[AI] Generating post... (Target: {scraped.get('title', 'N/A')[:15]}...)")
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-3-flash-preview')
            response = model.generate_content(prompt)
            
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                posts = json.loads(json_match.group())
                posts = sanitize_posts(posts, scraped.get("images", []), project_info)
                posts["target_date"] = data.get("target_date")
                posts["target_time"] = data.get("target_time")
                return posts
        except Exception as e:
            error_msg = str(e)
            lower_error = error_msg.lower()
            if "429" in error_msg:
                if "quota exceeded" in lower_error or "free_tier_requests" in lower_error or "resource_exhausted" in lower_error:
                    print("CRITICAL_ERROR: Gemini quota/token limit exceeded. Please try again tomorrow or check the API key/plan.")
                    sys.exit(42) # 일일 한도 초과 전용 종료 코드
                else:
                    wait_time = 20
                    print(f"[WARN] RPM limit reached. Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    if attempt == max_retries - 1:
                        print("CRITICAL_ERROR: Gemini rate limit persisted after retries.")
                        sys.exit(43)
            else:
                print(f"ERROR: {error_msg}")
                break
    return None

def save_posts(posts):
    """생성된 포스팅을 파일로 저장합니다."""
    if not posts: return
    
    gen_dir = "text_generated"
    if not os.path.exists(gen_dir): os.makedirs(gen_dir)
    
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    filename = f"campaign_{timestamp}.json"
    file_path = os.path.join(gen_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=4)
    print(f"SUCCESS: Post saved to {file_path}")

if __name__ == "__main__":
    campaign_data = read_campaign_data()
    result = generate_blog_posts(campaign_data)
    if result:
        save_posts(result)
