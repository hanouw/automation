import json
import os
import subprocess
import time


DEFAULT_NOTEBOOKLM_PROMPT = """아래 URL의 내용을 바탕으로 블로그 프로젝트 등록에 사용할 정보를 정리해줘.

요구사항:
- 서비스/인물/상품의 핵심 설명
- 홍보에 쓸 수 있는 강점
- 글 작성에 필요한 주요 키워드
- 불필요한 메뉴/푸터/로그인 문구 제외
- 한국어로 정리
"""


def env_bool(key, default=False):
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    return raw_value.lower() in ("1", "true", "yes", "y", "on")


def is_notebooklm_enabled():
    return env_bool("NOTEBOOKLM_MCP_ENABLED", False)


def notebooklm_required():
    return env_bool("NOTEBOOKLM_MCP_REQUIRED", False)


def _next_message(process, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = process.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise TimeoutError("NotebookLM MCP response timeout.")


def _send_message(process, message):
    process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
    process.stdin.flush()


def _wait_for_response(process, message_id, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        message = _next_message(process, max(0.1, deadline - time.time()))
        if message.get("id") == message_id:
            if "error" in message:
                raise RuntimeError(message["error"])
            return message.get("result", {})
    raise TimeoutError(f"NotebookLM MCP response timeout. id={message_id}")


def _extract_text(result):
    if isinstance(result, str):
        return result
    if not isinstance(result, dict):
        return ""

    if isinstance(result.get("structuredContent"), dict):
        structured = result["structuredContent"]
        if structured.get("content"):
            return str(structured["content"])
        if structured.get("text"):
            return str(structured["text"])

    content = result.get("content")
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(text for text in texts if text)

    if isinstance(content, str):
        return content
    return ""


def _parse_project_info(text):
    text = (text or "").strip()
    if not text:
        raise RuntimeError("NotebookLM MCP returned empty content.")

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            title = data.get("title") or data.get("name") or "NotebookLM 정리"
            content = data.get("content") or data.get("summary") or data.get("text") or text
            return {"title": str(title).strip(), "content": str(content).strip()}
    except json.JSONDecodeError:
        pass

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0].lstrip("# ").strip() if lines else "NotebookLM 정리"
    return {"title": title[:120], "content": text}


def fetch_project_info_with_notebooklm(url):
    command = os.getenv("NOTEBOOKLM_MCP_COMMAND", "").strip()
    tool_name = os.getenv("NOTEBOOKLM_MCP_TOOL", "").strip()
    timeout = int(os.getenv("NOTEBOOKLM_MCP_TIMEOUT", "60"))

    if not command:
        raise RuntimeError("NOTEBOOKLM_MCP_COMMAND is not set.")
    if not tool_name:
        raise RuntimeError("NOTEBOOKLM_MCP_TOOL is not set.")

    url_arg = os.getenv("NOTEBOOKLM_MCP_URL_ARG", "url")
    prompt_arg = os.getenv("NOTEBOOKLM_MCP_PROMPT_ARG", "prompt")
    prompt = os.getenv("NOTEBOOKLM_MCP_PROMPT", DEFAULT_NOTEBOOKLM_PROMPT)

    process = subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    try:
        _send_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "BlogAutomation", "version": "1.0"},
                },
            },
        )
        _wait_for_response(process, 1, timeout)
        _send_message(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        arguments = {
            url_arg: url,
            prompt_arg: prompt,
        }
        _send_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
        )
        result = _wait_for_response(process, 2, timeout)
        return _parse_project_info(_extract_text(result))
    finally:
        try:
            process.terminate()
        except Exception:
            pass
