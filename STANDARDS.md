# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/f0ce06bc9a8e3a51fc8260777b30750d368f4983
- 참조 커밋 SHA: `f0ce06bc9a8e3a51fc8260777b30750d368f4983` (workflow 호출도 이 SHA로 고정)
- 채택일: 2026-10-18 (채택 PR: #242, 최신 동기화: chore/update-shared-standards)
- profile: integration / ha
- 적용 점검표: [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md)
- 중앙 현황표: https://github.com/eigger/hass-repo-standards/blob/main/docs/adoption-status.md
- 조율: 주 에이전트 / 구현: 주 에이전트 / 독립 리뷰·검증: Opus 서브 에이전트
- 중앙 현황 갱신일: 2026-10-18
- 실제 기본 브랜치: `main`
- 테스트 경로: `tests/components/ble_esl/` (브라우저 테스트는 `tests/components/ble_esl/frontend/`)
- 변경 전 지원 최소 HA / 선언 근거: 2025.12.0 (`hacs.json`, README 설치 절)
- 적용 후 지원 최소 HA: **2025.12.0 유지** — 중간에 2026.10.0 상향을 시도했으나 사용자가 "가능하면 내리고"라고 해 되돌림. 테스트 헬퍼를 두 버전 호환으로 고쳐 2025.12.0에서 통과함을 확인
- current HA 테스트 환경: Python 3.14 / HA 2026.10.1 / pytest-homeassistant-custom-component 0.13.372
- 최소 HA 검증 환경: Python 3.13 / HA 2025.12.0 / plugin 0.13.298 (`requirements_test_min.txt`, `constraints/homeassistant-min.txt`), CI job `minimum-ha`
- 최소 package 검증: `blesession>=0.9.0`, `imagespec[datamatrix]>=1.1.0` — CI `dependency-modes: minimum`이 정확한 하한 설치

## 예외

| 규칙 ID | 이유 | 담당자 | 재검토 조건 |
|---|---|---|---|
| GOV-05 | 초기 CI·테스트 구조 이관은 서브 에이전트가 아닌 주 에이전트가 수행(사용자 지시: 작성 후 서브 에이전트 리뷰). 이후 감사 수정·README 재편은 구현 서브 에이전트가, 리뷰는 별도 Opus 에이전트가 수행 | @eigger | 다음 표준 재검토 때 구현도 위임 |
| HA-01, HA-08 | 엔티티 unique ID가 태그 MAC 마지막 8자리만 사용(`ble_esl_{identifier}_{key}`). 첫 2바이트만 다른 두 태그는 충돌 가능. 변경하려면 registry 마이그레이션·entry 버전 증가 필요 | @eigger | 충돌 사례 보고 또는 다음 데이터 형식 변경 시 |
| HA-13 | write-lock 스위치가 RestoreEntity 대신 `entry.data`를 갱신해 상태 보존 | @eigger | 데이터 형식 마이그레이션을 도입할 때 |
| HA-11 | 서비스 오류 메시지가 번역 키가 아닌 영어 문자열(`unknown_protocol`만 번역) | @eigger | 서비스 오류 번역 작업 시 |
| HA-10 | `designer/specs.py`가 공개 export가 없는 `imagespec.spec.UNSET`을 import | @eigger | imagespec가 공개 export를 제공할 때 |
