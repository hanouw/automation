# EXE 사용 방향

이 프로젝트는 로컬 Windows EXE 앱으로 운영하는 방향을 기준으로 정리했습니다.

## 실행 흐름

1. `BlogAutomation.exe` 실행
2. 자동으로 브라우저에서 `http://127.0.0.1:5000` 열림
3. `계정 추가 및 로그인`에서 티스토리 계정 별칭과 블로그 주소 입력
4. 열린 브라우저에서 카카오 로그인 완료
5. 로그인 창을 닫으면 `tistory_user_data/{계정명}`에 세션 저장
6. 프로젝트, 링크, SEO 문구, 예약 시간 입력 후 실행

## 빌드

PowerShell에서:

```powershell
.\build_exe.ps1
```

결과:

```text
dist/BlogAutomation/BlogAutomation.exe
```

## 중요한 폴더

EXE 옆의 아래 폴더는 삭제하지 마세요.

```text
source_data/
text_generated/
tistory_user_data/
tistory_debug/
.env
```

특히 `tistory_user_data/`에는 로그인 세션이 저장됩니다. 비밀번호급 민감 정보로 취급해야 합니다.

## 배포 시 주의

- `dist/BlogAutomation` 폴더 전체를 옮기세요.
- `BlogAutomation.exe`만 단독으로 복사하면 Playwright와 의존 파일이 빠질 수 있습니다.
- 새 PC에서는 계정 추가를 다시 눌러 로그인 세션을 새로 저장하는 편이 가장 안정적입니다.
