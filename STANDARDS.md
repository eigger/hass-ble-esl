# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/7acd9cab6ac774e4695f2c962e3d88b5faa4620d
- 참조 커밋 SHA: `7acd9cab6ac774e4695f2c962e3d88b5faa4620d` (workflow 호출도 이 SHA로 고정)
- 채택일: 2026-10-18 (채택 PR 미생성 — 로컬 브랜치 `chore/adopt-hass-repo-standards`, 미커밋)
- profile: integration / ha
- 적용 점검표: [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md)
- 중앙 현황표: https://github.com/eigger/hass-repo-standards/blob/main/docs/adoption-status.md
- 조율: 주 에이전트(Claude Code 세션) / 구현: 주 에이전트 직접(사용자가 "작성 후 서브 에이전트 리뷰"를 지시) / 독립 리뷰·검증: Opus 서브 에이전트
- 중앙 현황 갱신일: 미반영 (중앙 리포 push 미수행, 반영할 내용은 ADOPTION_CHECKLIST.md 하단)
- 실제 기본 브랜치: `main`
- 테스트 경로: `tests/components/ble_esl/` (브라우저 테스트는 `tests/frontend/`)
- 변경 전 지원 최소 HA / 선언 근거: 2025.12.0 (`hacs.json`, README 설치 절)
- 적용 후 지원 최소 HA: **2026.10.0** — 사용자가 "최소 버전을 올려"라고 명시 지시. 구버전 API 비호환 때문이 아님(2025.12.0 환경에서 같은 테스트 1095개가 통과함을 로컬 확인). 값은 사용자가 지정하지 않아 현재 테스트 버전으로 선택
- current HA 테스트 환경: Python 3.14 / HA 2026.10.0 / pytest-homeassistant-custom-component 0.13.371
- 최소 HA 검증 환경: current와 동일(최소=current이므로 단일 job)
- 최소 package 검증: `blesession>=0.9.0`, `imagespec[datamatrix]>=1.0.1` — CI `dependency-modes: minimum`이 정확한 하한 설치

## 예외

없음.
