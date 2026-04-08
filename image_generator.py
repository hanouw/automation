import os
import json
import time
from glob import glob
from datetime import datetime
import google.generativeai as genai  # 현재 환경에 설치된 라이브러리 유지
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
    exit(1)

genai.configure(api_key=api_key)

def get_latest_image_prompt():
    """최신 JSON 파일에서 이미지 프롬프트를 읽어옵니다."""
    files = glob("text_generated/*.json")
    if not files: return None
    latest_file = max(files, key=os.path.getctime)
    print(f"📄 최신 파일 로드: {latest_file}")
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("image_prompt")

def generate_image_nano_banana():
    prompt = get_latest_image_prompt()
    if not prompt:
        print("❌ 이미지 프롬프트가 없습니다. generator.py를 먼저 실행해 주세요.")
        return

    # 할당량 이슈가 적은 3.1 Flash Image 모델로 변경
    model_name = "gemini-3.1-flash-image-preview"
    print(f"🎨 Nano Banana 모델로 이미지 생성 중... (모델: {model_name})")
    print(f"💡 프롬프트: {prompt[:50]}...")

    try:
        model = genai.GenerativeModel(model_name)
        
        # 이미지 생성 요청
        response = model.generate_content(prompt)
        
        # 이미지 저장 경로 설정
        output_dir = "images_generated"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        now = datetime.now().strftime("%m%d_%H%M")
        image_path = os.path.join(output_dir, f"nano_{now}.png")

        # 결과 이미지 저장 (SDK 응답 구조에 따라 저장 방식이 결정됩니다)
        # 보통 response.candidates[0].content.parts 에 이미지 데이터가 담깁니다.
        if response.candidates:
            # Pillow 라이브러리를 사용하여 저장 (SDK 기본 방식)
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data'):
                    # 데이터가 직접 포함된 경우 처리 로직
                    pass
            
            # 모델이 이미지를 직접 리턴하는 최신 SDK 방식 적용
            # (주석: 실제 환경의 SDK 버전에 따라 아래 images 리스트를 활용합니다)
            if hasattr(response, 'images'):
                response.images[0].save(image_path)
                print(f"✅ 이미지 생성 및 저장 완료: {image_path}")
                return image_path
            else:
                print("❌ 응답 데이터에 이미지 형식이 포함되어 있지 않습니다.")
                print(f"응답 원문: {response.text[:100]}...")
        
    except Exception as e:
        print(f"❌ Nano Banana 실행 오류: {e}")
        print("💡 모델명이 다르거나 아직 계정에 해당 모델 권한이 없을 수 있습니다.")
        print(f"💡 {model_name}가 아닌 다른 모델명을 바꿔 시도해 볼까요?")
        return None

if __name__ == "__main__":
    generate_image_nano_banana()
