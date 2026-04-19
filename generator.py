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


def sanitize_posts(posts, allowed_images=None):
    if not isinstance(posts, dict):
        return posts
    allowed_image_keys = {image_key(url) for url in (allowed_images or [])}
    allowed_image_keys.discard("")

    for channel in ("naver", "tistory", "google"):
        section = posts.get(channel)
        if isinstance(section, dict):
            section["content"] = remove_bad_images_from_content(section.get("content", ""), allowed_image_keys)
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
            "project_info": project_info,
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
                posts = sanitize_posts(posts, scraped.get("images", []))
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
