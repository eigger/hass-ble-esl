# 공통 규칙 적용 체크리스트

[사용법과 판정 기준](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/checklist.md). 상태: `TODO` 미확인·미충족 / `PASS` 근거로 확인 / `EXCEPTION` / `N/A`. 원격 CI는 아직 실행되지 않았으므로 CI에 의존하는 항목은 `TODO`입니다.

## 검토 대상

| 항목 | 값 |
|---|---|
| 통합 리포 / 기본 브랜치 | eigger/hass-ble-esl / `main` |
| domain / 구현 경로 | `ble_esl` / `custom_components/ble_esl/` |
| 검토 대상 통합 커밋 / 채택 PR | 베이스 `0046ed6` + 미커밋 작업 트리 / PR 없음 |
| 검토한 표준 전체 SHA | `7acd9cab6ac774e4695f2c962e3d88b5faa4620d` (STANDARDS.md와 일치) |
| 검토일 / 조율 | 2026-10-18 / 주 에이전트 |
| 구현 / 독립 리뷰 | 주 에이전트(사용자 지시) / Opus 서브 에이전트 — 결과는 아래 "리뷰" 참조 |
| 중앙 현황표 반영 | 미반영 |
| 변경 전 지원 최소 HA | 2025.12.0 (`hacs.json`) |
| 유지·변경 지원 최소 | **2026.10.0으로 상향** — 사용자 명시 지시, 비호환 근거 없음(STANDARDS.md) |
| current 테스트 | Py 3.14 / HA 2026.10.0 / plugin 0.13.371 |
| 이전 검토 기록 | 최초 검토 |
| 채택 판정 | **이관 진행 중** (원격 CI·중앙 표 미완) |

## 항목

| 규칙 ID | 상태 | 근거 / 남은 작업 |
|---|---|---|
| GOV-01, GOV-02 | PASS | STANDARDS.md 작성, workflow는 `@7acd9ca…` 전체 SHA 고정, editor job의 외부 action도 full SHA |
| GOV-03 | TODO | 채택 PR 미생성. CHANGELOG `Unreleased`에 영향(최소 HA 상향) 기록 |
| GOV-04 | TODO | 중앙 표 미갱신 — 하단 "반영할 내용" |
| GOV-05 | TODO | 독립 리뷰 결과 반영 후 확정. 구현은 서브 에이전트가 아닌 주 에이전트가 수행(사용자 지시) |
| HA-01…HA-13 | TODO | 이번 작업은 CI·테스트 구조·문서 이관만 수행, 구현 코드(Core 대응 구조·migration 등)는 재감사하지 않음 |
| TEST-08 | PASS | `tests/components/ble_esl/` (+`__init__.py` 계층), pytest.ini `testpaths` 일치 |
| TEST-02, TEST-03, TEST-09 | PASS | `tests/components/ble_esl/conftest.py`가 `hass`·`enable_custom_integrations`·`MockConfigEntry` 사용, `setup_entry`가 `hass.config_entries.async_setup` 실행 (로컬 1097 passed) |
| TEST-04, HACS-01 | PASS(로컬) / TODO(CI) | 최소=current=2026.10.0 단일 환경. 상향은 명시 지시. 로컬: Py3.14/HA2026.10.0/plugin0.13.371 1097 passed. 원격 CI 미실행 |
| TEST-05, DEP-02, DEP-05 | PASS(로컬) / TODO(CI) | 로컬: imagespec 1.0.1·blesession 0.9.0 정확한 하한 + HA 2026.10.0에서 1095 passed(상향 전 커밋 기준). CI minimum 모드 미실행 |
| DEP-01, DEP-06 | PASS | runtime=manifest requirements, 테스트 requirements_test.txt, 린트 requirements_lint.txt 분리 |
| DEP-07, CI-06 | TODO | 공통 action이 HA component 요구사항 재귀 설치·`pip check` — 원격 실행 미확인 |
| HACS-01, HACS-02 | PASS | hacs.json `homeassistant: 2026.10.0`, README/LICENSE 루트 존재 |
| HACS-03, HACS-05 | TODO | 공통 validate 실행 미확인(원격). ignore 없음 |
| CI-01…CI-05, CI-07, CI-08, CI-12 | TODO | caller 작성 완료(PR·main push·dispatch, 최소 권한, 공통 workflow 호출). 원격 실행·required checks 이름 변경(`Tests`/`Validate` 하위 job 이름) 확인 필요 — branch protection 영구 대기 주의 |
| CI-09, CI-10, DEP-03, DEP-04 | TODO | update_dependencies.yml을 공통 dependency-update로 교체(주기 매일→주1회, bot branch `bot/manifest-dependencies`). dry-run 비교 미수행 |
| DOC-01, DOC-02, DOC-06 | PASS(부분) | README 영/한 상호 링크 유지, development.md에 검증 환경 표. README 구조 재편은 하지 않음(기존 구성 유지) |
| DOC-03, DOC-04, DOC-05 | PASS | `sync_badges.py --check` 통과, Usage 포함, Release 배지(실제 v1.3.0 릴리스 존재) |
| DOC-07 | PASS(부분) | README 영/한에 공통 Bluetooth 문서 링크, 기존 docs/troubleshooting.md가 모델별 진단 경로 제공 |
| HACS-04, REL-01…REL-03, CI-11 | N/A | 이번 작업은 릴리스·태그를 만들지 않음 |
| REL-04 | N/A | 이전/중단 리포 아님 |

## 반영할 중앙 현황표 내용 (미반영)

`hass-ble-esl / main`: 진행 중 — 기준 SHA 7acd9ca, 적용: CI 공통화·tests/components 이관·STANDARDS/체크리스트·배지, 최소 HA 2026.10.0 상향, 남은 일: 원격 CI 통과·required checks 갱신·dependency-update dry-run·중앙 표 갱신.
