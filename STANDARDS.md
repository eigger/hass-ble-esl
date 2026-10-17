# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/7acd9cab6ac774e4695f2c962e3d88b5faa4620d
- 참조 커밋 SHA: `7acd9cab6ac774e4695f2c962e3d88b5faa4620d` (workflow 호출도 이 SHA로 고정)
- 채택일: 2026-10-18 (채택 PR: #242)
- profile: integration / ha
- 적용 점검표: [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md)
- 중앙 현황표: https://github.com/eigger/hass-repo-standards/blob/main/docs/adoption-status.md
- 조율: 주 에이전트(Claude Code 세션) / 구현: 주 에이전트 직접(사용자가 "작성 후 서브 에이전트 리뷰"를 지시) / 독립 리뷰·검증: Opus 서브 에이전트
- 중앙 현황 갱신일: 미반영 (중앙 리포 push 미수행, 반영할 내용은 ADOPTION_CHECKLIST.md 하단)
- 실제 기본 브랜치: `main`
- 테스트 경로: `tests/components/ble_esl/` (브라우저 테스트는 `tests/frontend/`)
- 변경 전 지원 최소 HA / 선언 근거: 2025.12.0 (`hacs.json`, README 설치 절)
- 적용 후 지원 최소 HA: **2025.12.0 유지** — 중간에 2026.10.0 상향을 시도했으나 사용자가 "가능하면 내리고"라고 해 되돌림. 테스트 헬퍼를 두 버전 호환으로 고쳐 2025.12.0에서 통과함을 확인
- current HA 테스트 환경: Python 3.14 / HA 2026.10.1 / pytest-homeassistant-custom-component 0.13.372
- 최소 HA 검증 환경: Python 3.13 / HA 2025.12.0 / plugin 0.13.298 (`requirements_test_min.txt`, `constraints/homeassistant-min.txt`), CI job `minimum-ha`
- 최소 package 검증: `blesession>=0.9.0`, `imagespec[datamatrix]>=1.1.0` — CI `dependency-modes: minimum`이 정확한 하한 설치

## 예외

| 규칙 ID | 이유 | 담당자 | 재검토 조건 |
|---|---|---|---|
| GOV-05 | 구현을 서브 에이전트가 아닌 주 에이전트가 수행(사용자 지시: 작성 후 서브 에이전트 리뷰). 독립 리뷰는 Opus 서브 에이전트가 수행 | @eigger | 다음 표준 재검토 때 구현도 위임 | 
