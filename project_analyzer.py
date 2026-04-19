import json
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


PROJECT_REPORT_PROMPT = """
아래는 웹페이지에서 추출한 제목과 본문입니다.
본문에는 메뉴, 로그인, 회원가입, 푸터, 견적 폼, 반복 카테고리 문구가 섞여 있을 수 있습니다.

작업:
1. 불필요한 메뉴/로그인/푸터/견적 폼/반복 카테고리 문구를 제거하세요.
2. 회사/서비스/프로젝트의 핵심 정보를 블로그 자동화의 프로젝트 등록용 보조 자료로 짧게 정리하세요.
3. 홍보에 사용할 수 있는 강점, 대상 고객, SEO 키워드 후보를 뽑으세요.
4. 원문에 없는 실적, 수치, 보장 표현은 만들지 마세요.
5. 한국어로 작성하세요.
6. 이 보고서는 이후 블로그 글의 메인 주제가 아니라 브랜드/서비스 연결용 보조 자료입니다. 특정 글의 주제는 별도 참조 링크가 결정합니다.

반드시 아래 JSON 구조로만 응답하세요. 다른 텍스트는 포함하지 마세요.
{{
  "title": "프로젝트 보고서 제목",
  "content": "마크다운 보고서 본문"
}}

마크다운 보고서 본문은 아래 섹션을 포함하세요.
- [프로젝트 개요]
- [핵심 서비스]
- [주요 강점]
- [대상 고객]
- [SEO 키워드 후보]
- [홍보 연결 포인트]
- [사용 제한]

각 섹션은 짧고 실무적으로 작성하세요.
특히 [홍보 연결 포인트]에는 "참조 링크의 주제를 먼저 설명한 뒤 필요한 경우 프로젝트의 서비스와 자연스럽게 연결한다"는 원칙을 포함하세요.
[사용 제한]에는 프로젝트 정보를 글의 중심 소재처럼 반복하지 말라는 주의사항을 포함하세요.

[입력 제목]
{title}

[입력 URL]
{source_url}

[입력 본문]
{content}
"""


def compact_text(text, limit=6000):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit]


def parse_report_response(text):
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        raise ValueError("Gemini report response did not contain JSON.")

    data = json.loads(match.group())
    title = str(data.get("title") or "프로젝트 분석 보고서").strip()
    content = str(data.get("content") or "").strip()
    if not content:
        raise ValueError("Gemini report response content is empty.")
    return {"title": title, "content": content}


def analyze_project_info(scraped_data):
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    if not scraped_data:
        raise ValueError("scraped_data is required.")

    prompt = PROJECT_REPORT_PROMPT.format(
        title=scraped_data.get("title", ""),
        source_url=scraped_data.get("source_url", ""),
        content=compact_text(scraped_data.get("content", "")),
    )
    model = genai.GenerativeModel("gemini-3-flash-preview")
    response = model.generate_content(prompt)
    return parse_report_response(response.text)
