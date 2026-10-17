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
| 중앙 현황표 반영 | 2026-10-18 (`e83700c`) |
| 변경 전 지원 최소 HA | 2025.12.0 (`hacs.json`) |
| 유지·변경 지원 최소 | 2025.12.0 유지(상향 시도 후 사용자 요청으로 복원) |
| current 테스트 / 최소 테스트 | Py 3.14 / HA 2026.10.1 / plugin 0.13.372 ; Py 3.13 / HA 2025.12.0 / plugin 0.13.298 |
| 이전 검토 기록 | 최초 검토 |
| 채택 판정 | **이관 진행 중** (필수 TODO 남음: HA-01~13 구현 재감사, DOC-01/06/07) |

## 항목

| 규칙 ID | 상태 | 근거 / 남은 작업 |
|---|---|---|
| GOV-01, GOV-02 | PASS | STANDARDS.md 작성, workflow는 `@7acd9ca…` 전체 SHA 고정, editor job의 외부 action도 full SHA |
| GOV-03 | PASS | 채택 PR [#242](https://github.com/eigger/hass-ble-esl/pull/242)에서 영향(워크플로 이름·schedule·bot 브랜치 변경)을 본문과 CHANGELOG에 기록 |
| GOV-04 | PASS | 중앙 표의 hass-ble-esl 행을 2026-10-18 갱신(hass-repo-standards `e83700c`), 다른 행은 변경하지 않음 |
| GOV-05 | EXCEPTION | 구현은 주 에이전트(사용자 지시), 독립 리뷰는 Opus 서브 에이전트. STANDARDS.md 예외 참조. 리뷰 지적(최소 환경 주장 오류, imagespec 하한, 상태값, 옛 경로)은 수정함 |
| HA-01…HA-13 | TODO | 이번 작업은 CI·테스트 구조·문서 이관만 수행, 구현 코드(Core 대응 구조·migration 등)는 재감사하지 않음 |
| TEST-08 | PASS | `tests/components/ble_esl/` (+`__init__.py` 계층), pytest.ini `testpaths` 일치. 루트 `tests/conftest.py`(설명용 최소 파일)와 domain conftest에 fixture 배치 |
| TEST-02, TEST-03, TEST-09 | PASS | `tests/components/ble_esl/conftest.py`가 `hass`·`enable_custom_integrations`·`MockConfigEntry` 사용, `setup_entry`가 `hass.config_entries.async_setup` 실행 |
| TEST-04, HACS-01 | PASS | 지원 최소 2025.12.0 유지(hacs.json). CI [`minimum-ha`](https://github.com/eigger/hass-ble-esl/actions/runs/39075066369): Py3.13/HA 2025.12.0/plugin 0.13.298 통과, `current`: Py3.14/HA 2026.10.0/plugin 0.13.371 통과(expected-ha-version 검사 포함). 로컬도 1097 passed |
| TEST-05, DEP-02, DEP-05 | PASS | CI [`current / minimum`](https://github.com/eigger/hass-ble-esl/actions/runs/39075066369): manifest 하한(blesession 0.9.0, imagespec 1.1.0) 정확 설치 후 HA 2026.10.0 테스트 통과. 로컬 1097 passed, 3 skipped(test_design_templates의 automation 없음 케이스) |
| DEP-01, DEP-06 | PASS | runtime=manifest requirements, 테스트 requirements_test.txt, 린트 requirements_lint.txt 분리 |
| DEP-07, CI-06 | PASS | 공통 python-environment action이 manifest·HA component(bluetooth usb recorder diagnostics frontend panel_custom websocket_api) 요구사항을 설치하고 `pip check`를 실행(install.py:132), 위 CI job 모두 통과 |
| HACS-02 | PASS | 루트 README/LICENSE/hacs.json 존재 |
| HACS-03, HACS-05 | PASS | [validate / hacs·hassfest](https://github.com/eigger/hass-ble-esl/actions/runs/39075066366) 통과, ignore 없음 |
| CI-01…CI-05, CI-07, CI-08, CI-12 | PASS | caller가 PR·main push·dispatch(+validate schedule), contents:read, concurrency, 공통 workflow full SHA 호출, `ha` profile 필수 테스트, lint/test 병렬. main 763c323 [Tests](https://github.com/eigger/hass-ble-esl/actions/runs/39078324708)·[Validate](https://github.com/eigger/hass-ble-esl/actions/runs/39078324723) 성공. main에는 보호규칙·ruleset이 없어 갱신할 required checks 없음(CI-04 해당 변경 없음) |
| CI-09, CI-10, DEP-03, DEP-04 | PASS | updater가 선택 package(imagespec, blesession)의 연산자/extras를 보존하고 기본 브랜치 기준으로 동작. workflow_dispatch dry-run [https://github.com/eigger/hass-ble-esl/actions/runs/39078603182](https://github.com/eigger/hass-ble-esl/actions/runs/39078603182) 성공 — blesession 0.9.0·imagespec 1.1.0이 이미 PyPI 최신이라 PR 없음. 새 하한이 생기는 실제 PR 경로는 아직 미관찰 |
| DOC-01, DOC-06 | TODO | README 구조 재편은 하지 않음(기존 구성 유지). development.md에 검증 환경 표 추가 |
| DOC-02 | PASS | README 영/한 상호 링크·동일 정책 유지 |
| DOC-03, DOC-04, DOC-05 | PASS | `sync_badges.py --check` 통과, Usage 포함, Release 배지(실제 v1.3.0 릴리스 존재) |
| DOC-07 | TODO | README 영/한에 공통 Bluetooth 문서 링크 추가, 기존 docs/troubleshooting.md가 진단 경로 제공. 기기별 깨우기·인증 안내 전수 확인은 미수행 |
| HACS-04, REL-01…REL-03, CI-11 | N/A | 이번 작업은 릴리스·태그를 만들지 않음 |
| REL-04 | N/A | 이전/중단 리포 아님 |

## 남은 작업

| 규칙 ID / TODO | 남은 작업 | 담당자 | 완료 근거 |
|---|---|---|---|
| HA-01…HA-13, DOC-01, DOC-06, DOC-07 | 구현 코드 Core 대응 재감사, README 구조 재편, 기기별 깨우기·인증 안내 점검은 별도 작업 | @eigger | 후속 PR |
| 선택 | 브랜치 보호/required checks를 도입하면 현재 job 이름(`current / …`, `minimum-ha / …`, `validate / …`, `editor`) 사용 | @eigger | 설정 화면 |

## 중앙 현황표 반영 내용 (2026-10-18 반영, hass-repo-standards `e83700c`)

`hass-ble-esl / main`: 진행 중 — 기준 SHA 7acd9ca, 적용: CI 공통화·tests/components 이관·STANDARDS/체크리스트·배지, 최소 HA 2025.12.0 유지+최소 환경 CI 추가, 원격 CI 통과(run 39075066369). 남은 일: required checks 갱신·dependency-update dry-run·중앙 표 갱신·HA 재감사.
