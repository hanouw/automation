# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# 시스템 라이브러리 업데이트 및 필수 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치 (Chromium만)
RUN playwright install chromium

COPY . .

# 환경 변수 설정
ENV IS_DOCKER=true
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "app.py"]
