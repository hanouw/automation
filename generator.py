import os
import json
import re
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
    exit(1)

genai.configure(api_key=api_key)

def extract_json(text):
    try:
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match: return json_match.group(1)
        json_match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match: return json_match.group(1)
        start_idx, end_idx = text.find('{'), text.rfind('}')
        if start_idx != -1 and end_idx != -1: return text[start_idx:end_idx+1]
        return text
    except Exception: return text

def generate_blog_posts(keywords):
    # 이전에 잘 작동했던 안정적인 모델명 사용
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    prompt = f"""
    주제 키워드: {keywords}
    
    위 키워드를 바탕으로 네이버, 티스토리, 구글 스타일의 블로그 포스팅을 작성하고,
    본문에 삽입할 'Nano Banana(Gemini Image)' 모델용 이미지 생성 프롬프트를 영어로 작성해줘.
    반드시 아래의 JSON 형식으로만 응답해.
    
    [이미지 프롬프트 가이드]
    - 스타일: Realistic, High-quality photography, Cinematic lighting, 8k resolution.
    - 내용: {keywords}와 관련된 전문적이고 세련된 비즈니스/행사 장면.
    
    JSON 응답 형식:
    {{
      "naver": {{ "title": "제목", "content": "내용..." }},
      "tistory": {{ "title": "제목", "content": "내용 (HTML 포함)..." }},
      "google": {{ "title": "제목", "content": "내용 (HTML/FAQ 포함)..." }},
      "image_prompt": "masterpiece, best quality, professional photo of ..., highly detailed, cinematic lighting, 8k uhd"
    }}
    """

    print(f"'{keywords}' 키워드로 고품질 글과 이미지 프롬프트를 생성 중입니다...")
    
    try:
        response = model.generate_content(prompt)
        json_text = extract_json(response.text)
        return json.loads(json_text)
    except Exception as e:
        print(f"❌ 글 생성 중 오류 발생: {e}")
        return None

def save_posts(posts_data):
    if not posts_data: return
    output_dir = "text_generated"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    now = datetime.now().strftime("%m%d_%H%M")
    base_filename = f"blogtxt_{now}"
    
    # 통합 JSON 저장
    with open(os.path.join(output_dir, f"{base_filename}.json"), "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)
    
    # 플랫폼별 TXT 저장
    for platform in ["naver", "tistory", "google"]:
        if platform in posts_data:
            with open(os.path.join(output_dir, f"{base_filename}_{platform}.txt"), "w", encoding="utf-8") as f:
                f.write(f"제목: {posts_data[platform]['title']}\n\n{posts_data[platform]['content']}")
            
    print(f"\n✅ '{output_dir}' 폴더에 '{base_filename}.json' 파일이 생성되었습니다.")

if __name__ == "__main__":
    keywords = "연예인 섭외, 아츠로, 공연섭외"
    posts = generate_blog_posts(keywords)
    if posts: save_posts(posts)
