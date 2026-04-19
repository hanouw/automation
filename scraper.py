import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
EXCLUDE_IMAGE_KEYWORDS = ['logo', 'ico', 'icon', '아이콘', 'btn', 'common', 'header', 'footer', 'banner', 'nav', 'menu', 'sprite', 'sns']
PRIORITY_IMAGE_KEYWORDS = ['product', 'upload', 'editor', 'content', 'post', 'view', 'thumb', 'artist', 'person', 'profile']
IMAGE_ATTRS = ['src', 'data-src', 'data-lazy-src', 'original-src', 'data-original', 'data-url', 'data-image']

def normalize_url(url):
    url = (url or '').strip()
    if url and not url.startswith(('http://', 'https://')):
        return f"https://{url}"
    return url


def has_image_extension(image_url):
    path = urlsplit(image_url).path.lower()
    return path.endswith(IMAGE_EXTENSIONS)


def split_srcset(value):
    if not value:
        return []
    urls = []
    for item in value.split(','):
        candidate = item.strip().split()
        if candidate:
            urls.append(candidate[0])
    return urls


def image_text(img, full_src):
    fields = [
        full_src,
        img.get('alt') or '',
        img.get('title') or '',
        ' '.join(img.get('class') or []),
        img.get('id') or '',
    ]
    return ' '.join(fields).lower()


def should_skip_image(img, full_src):
    text = image_text(img, full_src)
    if any(k in text for k in EXCLUDE_IMAGE_KEYWORDS):
        return True
    return False


def image_score(img, full_src, index):
    text = image_text(img, full_src)
    score = 0
    if any(k in text for k in PRIORITY_IMAGE_KEYWORDS):
        score += 30
    if img.get('alt') or img.get('title'):
        score += 10

    for attr in ('width', 'height'):
        try:
            if int(img.get(attr) or 0) >= 250:
                score += 5
        except ValueError:
            pass

    return (-score, index)


def collect_image_candidates(soup, base_url):
    candidates = []
    index = 0

    for img in soup.find_all('img'):
        raw_urls = []
        for attr in IMAGE_ATTRS:
            value = img.get(attr)
            if value:
                raw_urls.append(value)
        raw_urls.extend(split_srcset(img.get('srcset')))
        raw_urls.extend(split_srcset(img.get('data-srcset')))

        for raw_url in raw_urls:
            full_src = urljoin(base_url, raw_url)
            candidates.append({
                "url": full_src,
                "img": img,
                "index": index,
            })
            index += 1

    for source in soup.find_all('source'):
        raw_urls = split_srcset(source.get('srcset')) + split_srcset(source.get('data-srcset'))
        for raw_url in raw_urls:
            full_src = urljoin(base_url, raw_url)
            candidates.append({
                "url": full_src,
                "img": source,
                "index": index,
            })
            index += 1

    return candidates


def filter_images(candidates):
    filtered = []
    seen = set()

    for candidate in candidates:
        full_src = candidate["url"]
        img = candidate["img"]

        if full_src in seen:
            continue
        seen.add(full_src)

        if not has_image_extension(full_src):
            continue
        if should_skip_image(img, full_src):
            continue

        filtered.append(candidate)

    filtered.sort(key=lambda item: image_score(item["img"], item["url"], item["index"]))
    return [item["url"] for item in filtered]


def scrape_url(url):
    """
    URL에서 제목, 본문 텍스트, 이미지 목록을 추출합니다.
    """
    try:
        url = normalize_url(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 제목 추출
        title = soup.title.string if soup.title else "제목 없음"
        
        # 2. 본문 텍스트 추출 (불필요한 태그 제거)
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=' ', strip=True)
        # 너무 긴 텍스트는 요약하거나 잘라냄 (Gemini 컨텍스트 제한 고려)
        text = text[:3000] 
        
        # 3. 모든 이미지 후보를 먼저 모은 뒤, 공통 규칙으로 필터링/정렬
        image_candidates = collect_image_candidates(soup, url)
        images = filter_images(image_candidates)
        
        return {
            "source_url": url,
            "title": title.strip(),
            "content": text,
            "images": images[:10] # 최대 10개
        }
    except Exception as e:
        print(f"❌ Scraping Error ({url}): {e}")
        return None

if __name__ == "__main__":
    # 테스트
    test_url = "https://www.google.com"
    print(scrape_url(test_url))
