# Portfolio (검은 배경 · 왼쪽 목록 / 가운데 이미지 / 오른쪽 텍스트)

## 새 작품 올리기
`content/works/` 안에 폴더 하나를 만들고 이미지와 `info.txt`를 넣습니다.

```
content/works/2026-my-new-work/
  info.txt
  cover.jpg      ← (선택) 홈 격자에 쓰일 썸네일. 없으면 첫 이미지
  01.jpg 02.jpg  ← 파일명 순서대로 표시
```

`info.txt` 형식 (오른쪽 열에 표시됨):

```
title: 작품 제목
year: 2026
medium: UV LED, photochromic paint
video: https://vimeo.com/123456789     ← (선택) 여러 줄 가능, YouTube도 가능
---
여기부터 자유 텍스트. 빈 줄 = 문단 구분.
```

- 폴더 이름이 정렬 기준입니다(큰 값이 위). `2026-…`처럼 연도로 시작하면 최신순이 됩니다.
- 영상 파일은 올리지 말고 Vimeo/YouTube 링크를 쓰세요(무료 호스팅 용량 한도 때문).
- 사진은 자동으로 800 / 1600 / 2400px 3단계(JPEG 품질 86)로 만들어지고, 브라우저가 화면에 맞는 것을 고릅니다(맥북 같은 레티나 화면은 2400px). 사진을 클릭하면 **원본**이 열립니다. 원본은 그대로 올려도 됩니다.
- 원본도 사이트에 함께 올라가므로 GitHub Pages 한도(사이트 1GB)를 봐야 합니다. 사진 1장이 약 10MB면 80~100장 정도가 한계입니다. 넘으면 원본을 5MB 안팎으로 줄여서 넣으세요.

## 유튜브 / Vimeo 영상 넣기
1. 영상을 YouTube(또는 Vimeo)에 먼저 올립니다. 공개 범위는 **일부 공개(Unlisted)**여도 됩니다. **비공개(Private)는 다른 사람에게 안 보입니다.**
2. YouTube 영상 아래 '공유'를 눌러 주소를 복사합니다.
3. 그 작품의 `info.txt` 위쪽(`---` 위)에 한 줄 추가합니다.
   ```
   video: https://youtu.be/영상ID
   ```
   영상이 여러 개면 `video:` 줄을 여러 번 쓰면 됩니다. 영상은 첫 번째 사진 바로 아래에 나옵니다.
- 인식하는 주소: `youtube.com/watch?v=…`, `youtu.be/…`, `youtube.com/shorts/…`, `vimeo.com/숫자`
- YouTube Studio → 해당 영상 → 세부정보 → '퍼가기 허용'이 켜져 있어야 합니다(기본값은 켜짐).

## 포트폴리오 PDF (영어·독일어·한국어)
`content/pdf/` 폴더에 `…_en.pdf`, `…_de.pdf`, `…_ko.pdf`로 끝나는 이름으로 넣으면 Portfolio(홈) 오른쪽 칸에 다운로드 링크가 생깁니다. 넣은 언어만 표시됩니다.

## 작품 사진 크게 보기
작품 페이지에서 사진을 클릭하면 전체화면이 됩니다. 오른쪽 절반 클릭·마우스 오른쪽 클릭·→ 키·스페이스 = 다음, 왼쪽 절반 클릭·← 키 = 이전, Esc = 닫기. 핸드폰은 좌우로 밀면 넘어갑니다.

## 핸드폰 화면 (자동 적용, 폭 860px 이하)
- 홈/About: 위에 이름 + **Menu** 버튼(누르면 전체 목록), 썸네일 2열, 아래에 소개 글·PDF 링크.
- 작품 페이지: 사진이 위에서 아래로 이어지고 **아래로 스크롤**해서 봅니다. 맨 아래 막대(제목·연도 + **Info +** 버튼)는 항상 고정되어 있고, 누르면 설명이 그 위로 올라옵니다. 스크롤 맨 끝에는 전체 작품 아카이브 격자가 나옵니다.
- 컴퓨터 화면은 그대로입니다.

## About / Contact 글쓰기
- `content/about.txt` → 가운데 칸 (Bio, CV, 전시 이력 등 긴 글)
- `content/contact.txt` → 오른쪽 칸 (메일, 링크)
- 빈 줄 = 새 문단, `# 제목` = 소제목, `**굵게**`, `*기울임*`, `[글자](https://주소)` = 링크. 메일 주소와 https 주소는 자동으로 링크가 됩니다.

## 글꼴·색 바꾸기
`build.py` 맨 위 CSS의 `:root{…}` 한 곳만 고치면 전체에 적용됩니다.
`--size`(글자 크기, 기본 11px), `--text`(본문 색), `--list`(작품 목록 색), `--media`(사진 칸 폭, 기본 910px).

## 아카이브 자동 갱신
작품 폴더를 추가하고 다시 빌드(GitHub에 올리면 자동)하면 모든 페이지의 아카이브 격자·왼쪽 목록·폰 Menu가 한꺼번에 갱신됩니다. 따로 고칠 곳이 없습니다.

## 다른 페이지
- `content/site.txt` 이름, 외부 링크(`link: 이름 | 주소`), 저작권 문구(`copyright: © 2026 Seunghoon Baek. All rights reserved.` — 안 쓰면 '© 올해 이름'이 자동으로 들어갑니다). 왼쪽 목록 맨 아래(폰은 Menu 맨 아래)에 표시됩니다.
- 왼쪽 작품 목록은 알파벳(A–Z)순, 홈 썸네일 격자는 최신순입니다.
- `content/home.txt` 홈 오른쪽 소개 문구
- `content/about.txt` / `content/contact.txt` 위 'About / Contact 글쓰기' 참고

## 로컬에서 보기
```
pip install pillow
python build.py            # docs/ 생성
python -m http.server -d docs
```
`make_samples.py`와 `content/works/` 안의 샘플 3개는 미리보기용입니다. 지우고 쓰세요.

## 무료 배포 (GitHub Pages)
1. GitHub에 새 저장소를 만들고 이 폴더 전체를 올립니다.
2. 저장소 Settings → Pages → Source를 **GitHub Actions**로 선택.
3. 이후 `content/`에 파일을 추가하고 `main`에 커밋하면 `.github/workflows/pages.yml`이 자동으로 빌드·배포합니다. 주소는 `https://<아이디>.github.io/<저장소>/`.
4. 도메인을 사고 싶어지면 Settings → Pages → Custom domain에서 연결합니다.

핸드폰에서는 GitHub 웹/앱으로 폴더에 이미지와 `info.txt`를 올리면 같은 방식으로 갱신됩니다.

한도(GitHub Pages): 사이트 1GB 이하, 월 대역폭 약 100GB(소프트 한도).
