import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path

from flask import Flask, Response, jsonify, make_response, render_template_string, request

from prompt_manager import DEFAULT_PROMPT_NAME
from prompt_manager import delete_prompt as delete_prompt_file
from prompt_manager import ensure_default_prompt, list_prompts, read_prompt, save_prompt as save_prompt_file
from project_analyzer import analyze_project_info
from scraper import scrape_url
from ui_template import HTML_TEMPLATE


def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_base_dir()
os.chdir(BASE_DIR)

DATA_DIR = BASE_DIR / "source_data"
ACCOUNT_DIR = BASE_DIR / "tistory_user_data"
GEN_DIR = BASE_DIR / "text_generated"
DEBUG_DIR = BASE_DIR / "tistory_debug"
PROMPT_DIR = BASE_DIR / "blog_prompts"

for folder in [DATA_DIR, ACCOUNT_DIR, GEN_DIR, DEBUG_DIR, PROMPT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
ensure_default_prompt(PROMPT_DIR)

app = Flask(__name__)
CANCELED_JOBS = set()
ACTIVE_PROCESSES = {}

def safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()


def safe_project_path(name):
    raw_name = (name or "").strip()
    if not raw_name:
        return None
    filename = Path(raw_name).name
    if not filename.endswith(".md"):
        filename = f"{safe_name(filename)}.md"
    target = (DATA_DIR / filename).resolve()
    target.relative_to(DATA_DIR.resolve())
    return target


def build_campaign_prompt(prompt_dir, selected_prompt):
    base_template = read_prompt(prompt_dir, DEFAULT_PROMPT_NAME)
    selected_prompt = (selected_prompt or "").strip()
    if not selected_prompt or selected_prompt == DEFAULT_PROMPT_NAME:
        return DEFAULT_PROMPT_NAME, base_template

    extra_template = read_prompt(prompt_dir, selected_prompt)
    combined_template = "\n\n".join([
        base_template,
        "### [ADDITIONAL PROMPT] ###",
        "아래 추가 프롬프트는 위 기본 홍보형 지침을 유지한 상태에서 글의 톤, 구조, 강조점을 보강하는 용도로만 적용하세요.",
        extra_template,
    ])
    return f"{DEFAULT_PROMPT_NAME} + {selected_prompt}", combined_template


def python_worker_command(worker_name, *args):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--worker", worker_name, *map(str, args)]
    return [sys.executable, "-u", str(BASE_DIR / "app.py"), "--worker", worker_name, *map(str, args)]


def process_env(extra=None):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONWARNINGS"] = "ignore::FutureWarning"
    if extra:
        env.update(extra)
    return env


def stream_worker(job_id, worker_name, args=None, env=None):
    args = args or []
    if job_id in CANCELED_JOBS:
        yield "__RETURN_CODE__:130\n"
        return

    process = subprocess.Popen(
        python_worker_command(worker_name, *args),
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=process_env(env),
    )
    ACTIVE_PROCESSES[job_id] = process
    try:
        for line in process.stdout:
            if job_id in CANCELED_JOBS:
                process.terminate()
                yield "[CANCEL] 실행 중인 작업자 프로세스를 종료했습니다.\n"
                break
            yield line
        process.wait()
        yield f"__RETURN_CODE__:{process.returncode}\n"
    finally:
        ACTIVE_PROCESSES.pop(job_id, None)


def run_and_stream(job_id, worker_name, args=None, env=None):
    returncode = None
    for line in stream_worker(job_id, worker_name, args, env):
        if line.startswith("__RETURN_CODE__:"):
            returncode = int(line.split(":", 1)[1])
            continue
        yield line
    return returncode


@app.route("/")
def index():
    profiles = sorted(p.name for p in DATA_DIR.glob("*.md") if p.name != "product_info.md")
    accounts = sorted(p.name for p in ACCOUNT_DIR.iterdir() if p.is_dir())
    if not accounts:
        accounts = ["default"]
    prompts = list_prompts(PROMPT_DIR)
    return render_template_string(
        HTML_TEMPLATE,
        profiles=profiles,
        accounts=accounts,
        prompts=prompts,
        default_prompt_name=DEFAULT_PROMPT_NAME,
    )


@app.route("/run_campaign", methods=["POST"])
def run_campaign():
    data = request.json or {}
    job_id = data.get("job_id") or str(time.time())
    CANCELED_JOBS.discard(job_id)

    def generate_logs():
        try:
            links = data.get("links", [])
            mode = data.get("mode", "generate")
            project = data.get("project")
            prompt_name, prompt_template = build_campaign_prompt(PROMPT_DIR, data.get("prompt"))
            generated_files = []
            known_files = set(glob(str(GEN_DIR / "*.json")))

            with open(DATA_DIR / project, "r", encoding="utf-8") as f:
                project_full_info = f.read()

            target_time = data.get("time") or "19:00"
            interval_days = int(data.get("interval", 1))
            yield "[Step 1] 글 생성을 시작합니다.\n"
            yield f"[*] 예약 기준: 간격 {interval_days}일, 시간 {target_time}\n"
            yield f"[*] 글 작성 형식: {prompt_name}\n"
            for i, url in enumerate(links):
                if job_id in CANCELED_JOBS:
                    yield "[CANCEL] 다음 링크 처리 전에 중단했습니다.\n"
                    return

                yield f"[*] {i + 1}/{len(links)} 링크 수집: {url}\n"
                scraped = scrape_url(url)
                if not scraped:
                    yield f"[!] 스크레이핑 실패, 건너뜀: {url}\n"
                    yield "[INFO] 이 단계에서는 Gemini를 호출하지 않았으므로 AI 토큰/할당량 소진 문제가 아닙니다.\n"
                    continue
                if scraped.get("source_url") != url:
                    yield f"[*] URL 보정: {scraped.get('source_url')}\n"

                post_date = (datetime.now() + timedelta(days=interval_days * i)).strftime("%Y-%m-%d")
                campaign_input = {
                    "project_info": project_full_info,
                    "scraped_data": scraped,
                    "seo_keywords": data.get("seo", ""),
                    "youtube_url": data.get("youtube", ""),
                    "prompt_name": prompt_name,
                    "prompt_template": prompt_template,
                    "target_date": post_date,
                    "target_time": target_time,
                }
                with open(DATA_DIR / "campaign_input.json", "w", encoding="utf-8") as f:
                    json.dump(campaign_input, f, ensure_ascii=False, indent=2)

                returncode = yield from run_and_stream(job_id, "generator")
                if returncode == 42:
                    yield "[CRITICAL] Gemini 일일 사용량/토큰 할당량 초과로 중단합니다. 내일 다시 시도하거나 API 플랜/키를 확인하세요.\n"
                    return
                if returncode == 43:
                    yield "[CRITICAL] Gemini 분당 요청 한도 또는 일시적 할당량 제한이 계속되어 중단합니다. 잠시 후 다시 시도하세요.\n"
                    return
                if returncode != 0:
                    yield f"[ERROR] 글 생성 실패. exit={returncode}\n"
                    continue

                new_files = sorted(set(glob(str(GEN_DIR / "*.json"))) - known_files, key=os.path.getctime)
                known_files.update(new_files)
                generated_files.extend(new_files)
                if not new_files:
                    yield "[ERROR] 글 생성 프로세스는 종료됐지만 새 JSON 파일이 없습니다. Gemini 응답 형식 또는 API 상태를 확인하세요.\n"
                yield f"[OK] {i + 1}번 글 생성 완료. 새 파일 {len(new_files)}개\n"

            if mode != "post":
                yield "\n[OK] 글 생성만 완료했습니다.\n"
                return

            if job_id in CANCELED_JOBS:
                yield "[CANCEL] 업로드 전에 중단했습니다.\n"
                return

            if not generated_files:
                yield "\n[SKIP] 생성된 글 파일이 없어 티스토리 업로드를 건너뜁니다.\n"
                return

            yield f"\n[Step 2] 티스토리 예약 업로드를 시작합니다. 대상 {len(generated_files)}개\n"
            returncode = yield from run_and_stream(
                job_id,
                "uploader",
                env={
                    "TISTORY_ACCOUNT_NAME": data.get("account", "default"),
                    "TISTORY_UPLOAD_FILES": json.dumps(generated_files, ensure_ascii=False),
                    "HEADLESS_MODE": "false",
                    "ALLOW_INTERACTIVE_LOGIN": "true",
                    "TISTORY_USE_STORAGE_STATE": "false",
                },
            )
            if returncode == 0:
                yield "\n[OK] 티스토리 업로드 프로세스가 종료되었습니다.\n"
            else:
                yield f"\n[ERROR] 티스토리 업로드 실패. exit={returncode}\n"
        except Exception as e:
            yield f"[SERVER ERROR] {e}\n"
        finally:
            CANCELED_JOBS.discard(job_id)

    return Response(generate_logs(), mimetype="text/plain")


@app.route("/cancel_campaign", methods=["POST"])
def cancel_campaign():
    job_id = (request.json or {}).get("job_id")
    if not job_id:
        return jsonify({"status": "error", "message": "job_id is required"})

    CANCELED_JOBS.add(job_id)
    process = ACTIVE_PROCESSES.get(job_id)
    if process and process.poll() is None:
        process.terminate()
    return jsonify({"status": "cancel_requested"})


@app.route("/add_account", methods=["POST"])
def add_account():
    data = request.json or {}
    name = safe_name(data.get("name", ""))
    blog_url = data.get("blog_url", "").strip()
    if not name or not blog_url:
        return jsonify({"status": "error", "message": "계정명과 블로그 주소가 필요합니다."})

    account_path = ACCOUNT_DIR / name
    account_path.mkdir(parents=True, exist_ok=True)
    with open(account_path / "config.json", "w", encoding="utf-8") as f:
        json.dump({"blog_url": blog_url}, f, ensure_ascii=False, indent=2)

    subprocess.Popen(
        python_worker_command("capture_session", name, str(account_path), blog_url),
        cwd=BASE_DIR,
        env=process_env({"HEADLESS_MODE": "false"}),
    )
    return jsonify({"status": "success", "account": name})


@app.route("/delete_account", methods=["POST"])
def delete_account():
    data = request.json or {}
    name = safe_name(data.get("name", ""))
    if not name:
        return jsonify({"status": "error", "message": "삭제할 계정명이 필요합니다."})
    if name == "default":
        return jsonify({"status": "error", "message": "default 계정은 삭제할 수 없습니다."})

    account_path = (ACCOUNT_DIR / name).resolve()
    account_root = ACCOUNT_DIR.resolve()

    try:
        account_path.relative_to(account_root)
    except ValueError:
        return jsonify({"status": "error", "message": "잘못된 계정 경로입니다."})

    if not account_path.exists() or not account_path.is_dir():
        return jsonify({"status": "error", "message": "계정 폴더가 존재하지 않습니다."})

    shutil.rmtree(account_path)
    return jsonify({"status": "success", "account": name})


@app.route("/save_profile", methods=["POST"])
def save_profile():
    data = request.json or {}
    name = safe_name(data.get("name", ""))
    content = data.get("content", "")
    if not name or not content:
        return jsonify({"status": "error", "message": "프로젝트명과 내용이 필요합니다."})
    target_path = DATA_DIR / f"{name}.md"
    original = data.get("original", "")
    if original:
        try:
            original_path = safe_project_path(original)
            if (
                original_path
                and original_path.exists()
                and original_path.name != "product_info.md"
                and original_path.resolve() != target_path.resolve()
            ):
                original_path.unlink()
        except (ValueError, OSError):
            return jsonify({"status": "error", "message": "기존 프로젝트 경로가 올바르지 않습니다."})
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    return jsonify({"status": "success", "file": target_path.name})


@app.route("/get_profile")
def get_profile():
    try:
        path = safe_project_path(request.args.get("name", ""))
    except ValueError:
        return jsonify({"status": "error", "message": "잘못된 프로젝트 경로입니다."})
    if not path or not path.exists() or path.name == "product_info.md":
        return jsonify({"status": "error", "message": "프로젝트 파일이 존재하지 않습니다."})
    return jsonify({
        "status": "success",
        "file": path.name,
        "name": path.stem,
        "content": path.read_text(encoding="utf-8"),
    })


@app.route("/delete_profile", methods=["POST"])
def delete_profile():
    try:
        path = safe_project_path((request.json or {}).get("name", ""))
    except ValueError:
        return jsonify({"status": "error", "message": "잘못된 프로젝트 경로입니다."})
    if not path or not path.exists() or path.name == "product_info.md":
        return jsonify({"status": "error", "message": "삭제할 프로젝트 파일이 존재하지 않습니다."})
    path.unlink()
    return jsonify({"status": "success", "file": path.name})


@app.route("/fetch_url_info", methods=["POST"])
def fetch_url_info():
    url = (request.json or {}).get("url", "")
    result = scrape_url(url)
    if not result:
        return jsonify({"status": "error", "message": "수집 실패"})

    try:
        report = analyze_project_info(result)
        return jsonify({
            "status": "success",
            "source": "gemini_report",
            "title": report["title"],
            "content": report["content"][:4000],
        })
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "source": "scraper",
        "title": result["title"],
        "content": result["content"][:1500],
    })


@app.route("/get_prompt")
def get_prompt():
    name = request.args.get("name", "")
    try:
        return jsonify({"status": "success", "name": name, "content": read_prompt(PROMPT_DIR, name)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/save_prompt", methods=["POST"])
def save_prompt():
    data = request.json or {}
    try:
        name = save_prompt_file(PROMPT_DIR, data.get("name", ""), data.get("content", ""))
        return jsonify({"status": "success", "name": name, "prompts": list_prompts(PROMPT_DIR)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/delete_prompt", methods=["POST"])
def delete_prompt():
    data = request.json or {}
    try:
        name = delete_prompt_file(PROMPT_DIR, data.get("name", ""))
        return jsonify({"status": "success", "name": name, "prompts": list_prompts(PROMPT_DIR)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/get_latest_preview")
def get_latest_preview():
    files = list(GEN_DIR.glob("*.json"))
    files.extend((GEN_DIR / "success").glob("*.json"))
    files = sorted(files, key=os.path.getmtime, reverse=True)
    if not files:
        response = make_response(jsonify({"preview": "", "file": "", "posts": {}}))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    try:
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        posts = {}
        for platform in ("naver", "tistory", "google"):
            section = data.get(platform, {})
            if not isinstance(section, dict):
                section = {}
            posts[platform] = {
                "title": section.get("title", ""),
                "content": section.get("content", ""),
            }
        tistory = posts.get("tistory", {})
        response = make_response(jsonify({
            "preview": f"Title: {tistory.get('title', '')}\\n\\n{tistory.get('content', '')}",
            "posts": posts,
            "file": str(files[0].relative_to(BASE_DIR)),
            "modified": int(os.path.getmtime(files[0])),
        }))
    except Exception:
        response = make_response(jsonify({"preview": "", "file": "", "posts": {}}))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def worker_main(worker_name, args):
    os.chdir(BASE_DIR)
    if worker_name == "generator":
        from generator import generate_blog_posts, read_campaign_data, save_posts

        result = generate_blog_posts(read_campaign_data())
        if result:
            save_posts(result)
        return 0

    if worker_name == "uploader":
        from tistory_uploader import upload_tistory_blog

        upload_tistory_blog()
        return 0

    if worker_name == "capture_session":
        from capture_tistory_session import main as capture_main

        sys.argv = ["capture_tistory_session.py", *args]
        capture_main()
        return 0

    print(f"Unknown worker: {worker_name}")
    return 2


def open_browser_later(port):
    time.sleep(1)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    if "--worker" in sys.argv:
        index = sys.argv.index("--worker")
        worker_name = sys.argv[index + 1]
        worker_args = sys.argv[index + 2:]
        raise SystemExit(worker_main(worker_name, worker_args))

    port = int(os.getenv("APP_PORT", "5000"))
    if os.getenv("OPEN_BROWSER", "true").lower() in ("1", "true", "yes", "on"):
        threading.Thread(target=open_browser_later, args=(port,), daemon=True).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
