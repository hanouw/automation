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
    """
    텍스트 내에서 JSON 부분만 추출하는 함수
    """
    try:
        # ```json ... ``` 블록 찾기
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # 그냥 ``` ... ``` 블록 찾기
        json_match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # 가장 처음 나타나는 { 와 마지막 } 사이 추출
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            return text[start_idx:end_idx+1]
        
        return text
    except Exception:
        return text

def generate_blog_posts(keywords):
    # 가장 안정적인 1.5 Flash 모델 사용
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = f"""
    주제 키워드: {keywords}
    
    위 키워드를 바탕으로 다음 3가지 스타일의 블로그 포스팅을 '매우 상세하고 풍부하게' 작성해줘.
    반드시 아래의 JSON 형식으로만 응답하고, JSON 외의 다른 설명은 하지 마.
    본문 내용에 줄바꿈은 \n 으로 표시해줘.
    
    1. [네이버 블로그 스타일]
    - 특징: 매우 친근한 말투, 풍부한 이모지 사용, 독자의 공감을 이끌어내는 서론.
    - 구성: 인사말 - 연예인/공연 섭외의 고민점 - '아츠로' 소개 및 강점(3가지 이상) - 결론 및 문의 유도.
    - 분량: 공백 포함 최소 800자 이상.

    2. [티스토리 스타일]
    - 특징: 전문적이고 분석적인 어조, 구조화된 정보 전달, HTML 태그(<h2>, <h3>, <ul>, <li>) 사용.
    - 구성: 행사 기획 가이드 서론 - 섭외 프로세스 단계별 분석 - 플랫폼 '아츠로'의 기술적/비즈니스적 강점 분석 - 맺음말.

    3. [구글 블로거(SEO) 스타일]
    - 특징: 검색 최적화(SEO) 고려, 핵심 키워드 반복, 명확한 소제목, FAQ 섹션 포함.
    - 구성: <h1> 메인 제목 - 핵심 체크리스트 - 왜 아츠로인가? - 자주 묻는 질문(FAQ 2개 이상) - 결론.

    JSON 응답 형식 (엄격히 준수):
    {{
      "naver": {{
        "title": "네이버 제목",
        "content": "본문 내용..."
      }},
      "tistory": {{
        "title": "티스토리 제목",
        "content": "본문 내용 (HTML 포함)..."
      }},
      "google": {{
        "title": "구글 제목",
        "content": "본문 내용 (HTML/FAQ 포함)..."
      }}
    }}
    """

    print(f"'{keywords}' 키워드로 고품질 블로그 글을 생성 중입니다...")
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text
        
        # JSON 부분만 정교하게 추출
        json_text = extract_json(raw_text)
        
        # JSON 파싱
        return json.loads(json_text)
    except json.JSONDecodeError as je:
        print(f"JSON 파싱 오류: {str(je)}")
        print("AI가 보내온 원문 데이터 일부를 확인해 보세요:")
        print(raw_text[:200] + "...")
        return None
    except Exception as e:
        print(f"알 수 없는 오류 발생: {str(e)}")
        return None

def save_posts(posts_data):
    if not posts_data:
        return
    
    output_dir = "text_generated"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    now = datetime.now().strftime("%m%d_%H%M")
    base_filename = f"blogtxt_{now}"
    
    # 1. 통합 JSON 저장
    json_path = os.path.join(output_dir, f"{base_filename}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)
    
    # 2. 플랫폼별 TXT 저장
    for platform, data in posts_data.items():
        txt_path = os.path.join(output_dir, f"{base_filename}_{platform}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"제목: {data['title']}\n\n")
            f.write(data['content'])
            
    print(f"\n✅ '{output_dir}' 폴더에 파일 생성이 완료되었습니다.")
    print(f"- 생성 파일: {base_filename}.json 및 각 플랫폼별 .txt")

if __name__ == "__main__":
    keywords = "연예인 섭외, 아츠로, 공연섭외"
    posts = generate_blog_posts(keywords)
    
    if posts:
        save_posts(posts)
    else:
        print("\n❌ 글 생성에 실패했습니다. 다시 시도해 주세요.")
