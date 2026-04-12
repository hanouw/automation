import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_token():
    print("\n" + "="*40)
    print(" 🔍 Gemini API 토큰 상태 점검 (2026 Ver.) ")
    print("="*40)

    # 1. 환경 변수 로드
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("❌ 오류: .env 파일에 GEMINI_API_KEY가 설정되어 있지 않습니다.")
        return

    print(f"🔑 API Key 로드 완료 (앞 5자리: {api_key[:5]}...)")

    # 2. Gemini 설정 및 테스트 요청
    try:
        genai.configure(api_key=api_key)
        
        # 현재 프로젝트(generator.py)에서 사용 중인 최신 모델로 테스트
        # 404 에러 방지를 위해 gemini-3-flash-preview 사용
        model_name = 'gemini-3-flash-preview'
        print(f"🔄 모델 [{model_name}]에 테스트 요청 중...")
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello! This is a simple API quota test. Answer with one word 'SUCCESS'.")
        
        if response and response.text:
            print("\n✅ [결과: 성공] 토큰이 정상이며 사용 가능한 상태입니다!")
            print(f"💬 응답 내용: {response.text.strip()}")
        else:
            print("\n⚠️ [결과: 불명확] 응답은 왔으나 내용이 없습니다.")

    except Exception as e:
        error_msg = str(e)
        print("\n❌ [결과: 실패] 토큰 사용이 불가능합니다.")
        
        if "429" in error_msg:
            print("💡 원인: Quota Exceeded (오늘의 무료 한도 소진)")
        elif "404" in error_msg:
            print(f"💡 원인: Model Not Found (모델을 찾을 수 없음: {model_name})")
            print("   - API가 지원하는 최신 모델 이름을 확인해야 합니다.")
        elif "403" in error_msg:
            print("💡 원인: Invalid API Key (잘못된 키 혹은 권한 없음)")
        else:
            print(f"💡 상세 에러 내용: {error_msg}")

    print("\n※ 참고: google.generativeai 경고는 라이브러리 업데이트 권고이며 현재 실행과는 무관합니다.")
    print("="*40 + "\n")

if __name__ == "__main__":
    test_gemini_token()
