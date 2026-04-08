import os
import json
import re
import sys
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# 환경 변수 로드 (로컬: .env / 배포: st.secrets)
def get_env_var(key):
    # 1. Streamlit Secrets 확인
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    # 2. OS 환경 변수 또는 .env 확인
    load_dotenv()
    return os.getenv(key)

api_key = get_env_var("GEMINI_API_KEY")
if not api_key:
    print(f"Error: {key} not found in environment or secrets.")
    sys.exit(1)

genai.configure(api_key=api_key)

def read_product_info():
    folder_path = "source_data"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    file_path = os.path.join(folder_path, "product_info.md")
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found.")
        return None
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return content if content else None

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

def generate_blog_posts(info_text):
    # Free Tier에서 안정적인 모델 사용
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    if info_text:
        context_prompt = f"Data:\n{info_text}\nBased on this,"
    else:
        context_prompt = "Based on 'Artist booking, Artsro',"

    prompt = f"""
    {context_prompt} write detailed blog posts for Naver, Tistory, and Google Blogger in Korean.
    Return ONLY JSON format.
    
    1. [Naver Style]: Friendly, emojis allowed in content.
    2. [Tistory Style]: Professional, use HTML tags, include <!-- IMAGE_PLACEHOLDER_1 --> twice.
    3. [Google Style]: SEO optimized, FAQ included.

    Response JSON:
    {{
      "naver": {{ "title": "...", "content": "..." }},
      "tistory": {{ "title": "...", "content": "..." }},
      "google": {{ "title": "...", "content": "..." }},
      "image_prompt": "english image prompt..."
    }}
    """

    print("Generating content via Gemini AI...")
    
    try:
        response = model.generate_content(prompt)
        json_text = extract_json(response.text)
        return json.loads(json_text)
    except Exception as e:
        print(f"Error during generation: {e}")
        return None

def save_posts(posts_data):
    if not posts_data: return
    output_dir = "text_generated"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    now = datetime.now().strftime("%m%d_%H%M")
    base_filename = f"blogtxt_{now}"
    
    with open(os.path.join(output_dir, f"{base_filename}.json"), "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)
    
    for platform in ["naver", "tistory", "google"]:
        if platform in posts_data:
            with open(os.path.join(output_dir, f"{base_filename}_{platform}.txt"), "w", encoding="utf-8") as f:
                f.write(f"Title: {posts_data[platform]['title']}\n\n{posts_data[platform]['content']}")
            
    print(f"Success: {base_filename}.json created.")

if __name__ == "__main__":
    info_text = read_product_info()
    posts = generate_blog_posts(info_text)
    if posts: 
        save_posts(posts)
