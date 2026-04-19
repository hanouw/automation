import os
import json
import re
import sys
import time
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# 1. 설정 및 로드
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

BAD_IMAGE_KEYWORDS = ['logo', 'ico', 'icon', '아이콘', 'btn', 'common', 'header', 'footer', 'banner', 'nav', 'menu', 'sprite', 'sns']


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

def generate_blog_posts(data, max_retries=3):
    """Gemini API를 사용하여 포스팅을 생성합니다. (429 에러 시 재시도 로직 포함)"""
    if not data: return None
    
    project_info = data.get("project_info", "")
    scraped = data.get("scraped_data", {})
    seo_keywords = data.get("seo_keywords", "")
    youtube_url = data.get("youtube_url", "")
    
    image_list_str = "\n".join([f"- {url}" for url in scraped.get("images", [])])

    prompt = f"""
당신은 대한민국 최고의 블로그 마케팅 전문가이자 SEO 전문가입니다. 
아래 제공된 [프로젝트 정보]와 [참조 데이터]를 활용하여 최상의 블로그 포스팅을 작성해 주세요.

### 핵심 지침 (Instructions) ###
1. **내용 재구성**: [참조 데이터]의 내용을 그대로 베끼지 말고, [프로젝트 정보]의 홍보 목적에 맞게 매력적으로 각색하세요.
2. **SEO 최적화**: [SEO 핵심 문구]를 본문에 자연스럽게 녹여내세요 (3~5회 권장).
3. **이미지 배치**: [이미지 목록]에 있는 URL들을 본문 중간중간에 <img> 태그로 넣으세요. 이미지 앞 뒤로 한 줄씩 띄우세요.
   - **중요**: 각 <img> 태그에는 이미지의 시각적 내용과 [SEO 핵심 문구]를 결합한 'alt' 속성을 반드시 구체적으로 작성하세요.
   - **금지**: [이미지 목록]에 없는 이미지 URL은 절대 만들거나 추측하지 마세요.
   - **금지**: src 또는 alt에 logo, ico, icon, 아이콘, btn, common, header, footer, banner, nav, menu, sprite, sns가 들어가는 이미지는 절대 사용하지 마세요.
4. **유튜브 임베드**: [유튜브 URL]이 있다면 **반드시 본문 내용이 모두 끝난 뒤, 하단 고정 홍보문구 바로 위**에 <iframe> 형태의 티스토리 호환 임베드 코드를 삽입하세요.
5. **마무리**: 글의 마지막에는 반드시 [프로젝트 정보]의 '하단 고정 홍보문구'를 그대로 넣으세요.
6. **형식**: 티스토리는 HTML 형식, 네이버는 가독성 좋은 텍스트(이모지 포함) 형식으로 작성하세요.

### 입력 데이터 (Input Data) ###
[프로젝트 및 홍보 정보]
{project_info}

[참조 데이터 (URL 추출)]
- 원천: {scraped.get("source_url")}
- 제목: {scraped.get("title")}
- 내용: {scraped.get("content")}

[이미지 목록]
{image_list_str}

[SEO 핵심 문구]
{seo_keywords}

[유튜브 URL]
{youtube_url}

### 출력 형식 (JSON) ###
반드시 아래 구조의 JSON으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "naver": {{ "title": "네이버 제목", "content": "네이버 본문" }},
  "tistory": {{ "title": "티스토리 제목", "content": "티스토리 HTML 본문" }},
  "google": {{ "title": "SEO 제목", "content": "SEO 최적화 본문" }}
}}
"""
    
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
