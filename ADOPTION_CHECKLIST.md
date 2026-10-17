# 공통 규칙 적용 체크리스트

[사용법과 판정 기준](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/checklist.md). 상태: `TODO` 미확인·미충족 / `PASS` 근거로 확인 / `EXCEPTION` / `N/A`. 원격 CI는 아직 실행되지 않았으므로 CI에 의존하는 항목은 `TODO`입니다.

## 검토 대상

| 항목 | 값 |
|---|---|
| 통합 리포 / 기본 브랜치 | eigger/hass-ble-esl / `main` |
| domain / 구현 경로 | `ble_esl` / `custom_components/ble_esl/` |
| 검토 대상 통합 커밋 / 채택 PR | 베이스 `0046ed6` / [#242](https://github.com/eigger/hass-ble-esl/pull/242) |
| 검토한 표준 전체 SHA | `7acd9cab6ac774e4695f2c962e3d88b5faa4620d` (STANDARDS.md와 일치) |
| 검토일 / 조율 | 2026-10-18 / 주 에이전트 |
| 구현 / 독립 리뷰 | 주 에이전트(사용자 지시) / Opus 서브 에이전트 — 지적 사항은 항목 표의 GOV-05 행 참조 |
| 중앙 현황표 반영 | 미반영 |
| 변경 전 지원 최소 HA | 2025.12.0 (`hacs.json`) |
| 유지·변경 지원 최소 | 2025.12.0 유지(상향 시도 후 사용자 요청으로 복원) |
| current 테스트 / 최소 테스트 | Py 3.14 / HA 2026.10.0 / plugin 0.13.371 ; Py 3.13 / HA 2025.12.0 / plugin 0.13.298 |
| 이전 검토 기록 | 최초 검토 |
| 채택 판정 | **이관 진행 중** (원격 CI·중앙 표 미완) |

## 항목

| 규칙 ID | 상태 | 근거 / 남은 작업 |
|---|---|---|
| GOV-01, GOV-02 | PASS | STANDARDS.md 작성, workflow는 `@7acd9ca…` 전체 SHA 고정, editor job의 외부 action도 full SHA |
| GOV-03 | TODO | 채택 PR [#242](https://github.com/eigger/hass-ble-esl/pull/242) 진행 중. CHANGELOG `Unreleased`에 변경 기록(최소 HA는 유지) |
| GOV-04 | TODO | 중앙 표 미갱신 — 하단 "반영할 내용" |
| GOV-05 | EXCEPTION | 구현은 주 에이전트(사용자 지시), 독립 리뷰는 Opus 서브 에이전트. STANDARDS.md 예외 참조. 리뷰 지적(최소 환경 주장 오류, imagespec 하한, 상태값, 옛 경로)은 수정함 |
| HA-01…HA-13 | TODO | 이번 작업은 CI·테스트 구조·문서 이관만 수행, 구현 코드(Core 대응 구조·migration 등)는 재감사하지 않음 |
| TEST-08 | PASS | `tests/components/ble_esl/` (+`__init__.py` 계층), pytest.ini `testpaths` 일치. 루트 `tests/conftest.py`(설명용 최소 파일)와 domain conftest에 fixture 배치 |
| TEST-02, TEST-03, TEST-09 | PASS | `tests/components/ble_esl/conftest.py`가 `hass`·`enable_custom_integrations`·`MockConfigEntry` 사용, `setup_entry`가 `hass.config_entries.async_setup` 실행 |
| TEST-04, HACS-01 | TODO | 지원 최소 2025.12.0 유지, 별도 `minimum-ha` job. 로컬: current(2026.10.0/py3.14/0.13.371)와 최소(2025.12.0/py3.13/0.13.298/blesession 0.9.0/imagespec 1.1.0) 모두 1097 passed, 3 skipped. 원격 CI 미실행이라 PASS 아님 |
| TEST-05, DEP-02, DEP-05 | TODO | 로컬 Py3.14 / HA 2026.10.0 / plugin 0.13.371 / blesession 0.9.0 / imagespec 1.1.0(manifest 하한 `>=0.9.0`, `>=1.1.0`)에서 1097 passed, 3 skipped (3 skip은 test_design_templates의 automation 없음 케이스). CI minimum 모드 미실행 |
| DEP-01, DEP-06 | PASS | runtime=manifest requirements, 테스트 requirements_test.txt, 린트 requirements_lint.txt 분리 |
| DEP-07, CI-06 | TODO | 공통 action이 HA component 요구사항 재귀 설치·`pip check` — 원격 실행 미확인 |
| HACS-02 | PASS | 루트 README/LICENSE/hacs.json 존재 |
| HACS-03, HACS-05 | TODO | 공통 validate 실행 미확인(원격). ignore 없음 |
| CI-01…CI-05, CI-07, CI-08, CI-12 | TODO | caller 작성 완료(PR·main push·dispatch, 최소 권한, 공통 workflow 호출). 원격 실행·required checks 이름 변경 확인 필요 — branch protection 영구 대기 주의. 린트 Python은 공통 기본 3.13(기존 3.12) |
| CI-09, CI-10, DEP-03, DEP-04 | TODO | update_dependencies.yml을 공통 dependency-update로 교체(주기 매일→주1회, bot branch `bot/manifest-dependencies`). dry-run 비교 미수행 |
| DOC-01, DOC-06 | TODO | README 구조 재편은 하지 않음(기존 구성 유지). development.md에 검증 환경 표 추가 |
| DOC-02 | PASS | README 영/한 상호 링크·동일 정책 유지 |
| DOC-03, DOC-04, DOC-05 | PASS | `sync_badges.py --check` 통과, Usage 포함, Release 배지(실제 v1.3.0 릴리스 존재) |
| DOC-07 | TODO | README 영/한에 공통 Bluetooth 문서 링크 추가, 기존 docs/troubleshooting.md가 진단 경로 제공. 기기별 깨우기·인증 안내 전수 확인은 미수행 |
| HACS-04, REL-01…REL-03, CI-11 | N/A | 이번 작업은 릴리스·태그를 만들지 않음 |
| REL-04 | N/A | 이전/중단 리포 아님 |

## 반영할 중앙 현황표 내용 (미반영)

`hass-ble-esl / main`: 진행 중 — 기준 SHA 7acd9ca, 적용: CI 공통화·tests/components 이관·STANDARDS/체크리스트·배지, 최소 HA 2025.12.0 유지+최소 환경 CI 추가, 남은 일: 원격 CI 통과·required checks 갱신·dependency-update dry-run·중앙 표 갱신.
