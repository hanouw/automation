# NotebookLM MCP 설정 안내

현재 앱은 프로젝트 등록 모달의 `URL 정보 가져오기`에서 NotebookLM MCP를 우선 사용할 수 있도록 준비되어 있다. 단, NotebookLM MCP 서버가 실제로 설치/연결되어 있어야 한다.

## 현재 코드 동작

`NOTEBOOKLM_MCP_ENABLED=true`이면 앱은 `/fetch_url_info` 요청에서 NotebookLM MCP를 먼저 호출한다.

NotebookLM MCP 호출이 성공하면:

```text
NotebookLM MCP로 프로젝트 정보를 가져왔습니다.
```

NotebookLM MCP가 꺼져 있거나 실패했고 `NOTEBOOKLM_MCP_REQUIRED=false`이면 기존 `scraper.py` 방식으로 fallback한다.

fallback이면:

```text
기본 스크래퍼로 프로젝트 정보를 가져왔습니다.
```

## .env에 추가할 값

프로젝트 루트의 `.env` 파일에 아래 값을 추가한다.

```env
# NotebookLM MCP 사용 여부
NOTEBOOKLM_MCP_ENABLED=true

# true면 NotebookLM MCP 실패 시 scraper fallback을 하지 않고 에러 처리
# false면 MCP 실패 시 기존 scraper.py 방식으로 URL 정보를 가져옴
NOTEBOOKLM_MCP_REQUIRED=false

# NotebookLM MCP 서버 실행 명령
# 실제 설치한 NotebookLM MCP 서버 명령으로 바꿔야 함
NOTEBOOKLM_MCP_COMMAND=npx -y <notebooklm-mcp-server-package-or-command>

# NotebookLM MCP 서버에서 URL 분석/요약에 사용하는 tool 이름
# 실제 서버의 tools/list 결과에 맞춰 바꿔야 함
NOTEBOOKLM_MCP_TOOL=<tool_name>

# MCP tool arguments 이름
# 대부분 url/prompt 형태를 쓰지만, 서버마다 다르면 바꿔야 함
NOTEBOOKLM_MCP_URL_ARG=url
NOTEBOOKLM_MCP_PROMPT_ARG=prompt

# 응답 대기 시간, 초
NOTEBOOKLM_MCP_TIMEOUT=60
```

## 꼭 확인해야 하는 것

NotebookLM MCP 서버마다 tool 이름과 argument 이름이 다를 수 있다.

예를 들어 서버의 tool 이름이 `summarize_url`이고 인자가 `sourceUrl`, `instruction`이라면:

```env
NOTEBOOKLM_MCP_TOOL=summarize_url
NOTEBOOKLM_MCP_URL_ARG=sourceUrl
NOTEBOOKLM_MCP_PROMPT_ARG=instruction
```

처럼 바꿔야 한다.

## 현재 Codex 세션 상태

현재 Codex 세션에서 확인한 MCP resources/templates는 비어 있다. 즉 이 PC의 Codex 앱에는 아직 NotebookLM MCP가 연결되어 있지 않은 상태다.

앱 코드에는 NotebookLM MCP 호출 경로가 추가되어 있지만, 실제 사용하려면 별도의 NotebookLM MCP 서버 설치와 `.env` 설정이 필요하다.

## 관련 코드

- `notebooklm_mcp_client.py`: NotebookLM MCP stdio 서버 호출 클라이언트.
- `app.py`의 `/fetch_url_info`: NotebookLM MCP 우선 호출, 실패 시 scraper fallback.
- `ui_template.py`: 프로젝트 등록 모달에서 사용 경로를 상태 메시지로 표시.

## 주의

- EXE로 빌드하면 `.env`는 `dist/BlogAutomation/.env`로 복사된다.
- NotebookLM MCP 서버 자체는 EXE 안에 포함되지 않는다.
- EXE를 다른 PC로 옮길 경우 해당 PC에도 `NOTEBOOKLM_MCP_COMMAND`가 실행 가능한 환경이 필요하다.
- Node 기반 MCP 서버라면 Node.js와 해당 MCP 패키지가 설치되어 있어야 한다.

