# 공통 규칙 적용 체크리스트

[사용법과 판정 기준](https://github.com/eigger/hass-repo-standards/blob/f0ce06bc9a8e3a51fc8260777b30750d368f4983/docs/checklist.md). 상태: `TODO` 미확인·미충족 / `PASS` 근거로 확인 / `EXCEPTION` / `N/A`. 원격 CI는 아직 실행되지 않았으므로 CI에 의존하는 항목은 `TODO`입니다.

## 검토 대상

| 항목 | 값 |
|---|---|
| 통합 리포 / 기본 브랜치 | eigger/hass-ble-esl / `main` |
| domain / 구현 경로 | `ble_esl` / `custom_components/ble_esl/` |
| 검토 대상 통합 커밋 / 채택 PR | `f2b389a` (main) / PR (최신 표준 재동기화) |
| 검토한 표준 전체 SHA | `f0ce06bc9a8e3a51fc8260777b30750d368f4983` (STANDARDS.md와 일치) |
| 검토일 / 조율 | 2026-10-18 / 주 에이전트 |
| 구현 / 독립 리뷰 | 주 에이전트 / Opus 서브 에이전트 — 지적 사항은 항목 표의 GOV-05 행 참조 |
| 중앙 현황표 반영 | 2026-10-18 |
| 변경 전 지원 최소 HA | 2025.12.0 (`hacs.json`) |
| 유지·변경 지원 최소 | 2025.12.0 유지(상향 시도 후 사용자 요청으로 복원) |
| current 테스트 / 최소 테스트 | Py 3.14 / HA 2026.10.1 / plugin 0.13.372 ; Py 3.13 / HA 2025.12.0 / plugin 0.13.298 |
| 이전 검토 기록 | 최초 검토(PR #242, #248) 후 최신 표준 재동기화 |
| 채택 판정 | **예외가 있는 채택** (필수 TODO 없음, EXCEPTION: HA-01/08·HA-10·HA-11·HA-13 일부, GOV-05) |

## 항목

| 규칙 ID | 상태 | 근거 / 남은 작업 |
|---|---|---|
| GOV-01, GOV-02 | PASS | STANDARDS.md 작성, workflow는 `@f0ce06b…` 전체 SHA 고정, editor job의 외부 action도 full SHA |
| GOV-03 | PASS | 채택 PR [#242](https://github.com/eigger/hass-ble-esl/pull/242) 및 재동기화 PR에서 영향(README 템플릿 영역화, 테스트 구조 일치, validate compliance 검사 추가)을 기록 |
| GOV-04 | PASS | 중앙 표의 hass-ble-esl 행을 2026-10-18 갱신, 다른 행은 변경하지 않음 |
| GOV-05 | EXCEPTION | 초기 CI·구조 이관은 주 에이전트가 직접 구현(사용자 지시), 감사 수정·README 재편은 구현 서브 에이전트가 수행하고 별도 Opus 에이전트가 독립 리뷰, 독립 리뷰는 Opus 서브 에이전트. STANDARDS.md 예외 참조. 리뷰 지적(최소 환경 주장 오류, imagespec 하한, 상태값, 옛 경로)은 수정함 |
| HA-01…HA-13 | EXCEPTION | 2026-10-18 독립 감사(Opus, 읽기 전용) 후 [#247](https://github.com/eigger/hass-ble-esl/pull/247)로 수정·독립 리뷰. 수정: HA-02 `integration_type`, HA-06 PNG executor·취소 전파, HA-07 폴링 제거, HA-08 Failure Count `total_increasing`, HA-09 connectable 목록, HA-10 비공개 `imagespec.schema` import 제거, HA-11 서비스 스키마 검증, HA-12 diagnostics MAC 마스킹·재시도 로그. 미해결은 STANDARDS.md 예외(HA-01/08 unique_id 8자리, HA-13 write-lock RestoreEntity, HA-11 서비스 오류 번역, HA-10 `imagespec.spec.UNSET`). reauth/reconfigure/migration은 N/A(태그 인증 없음, 모델은 options, 데이터 형식 변경 없음) |
| TEST-08, TEST-03 | PASS | 루트 `tests/conftest.py`는 중앙 템플릿과 100% 일치(TEST-03), domain conftest에 `domain-fixtures` 스켈레톤(TEST-08), 빈 `__init__.py` 계층 유지, pytest.ini `testpaths` 일치 |
| TEST-02, TEST-09 | PASS | `tests/components/ble_esl/conftest.py`가 `hass`·`enable_custom_integrations`·`MockConfigEntry` 사용, `setup_entry`가 `hass.config_entries.async_setup` 실행 |
| TEST-01, TEST-06, TEST-07 | PASS | 실제 HA fixture 기반 config flow·setup/unload/reload·서비스 회귀 테스트 존재, #247에서 diagnostics 마스킹·재시도 로그·스키마·취소·패널 롤백 회귀 추가(구 코드에서 실패 확인). migration 테스트는 migration이 없어 N/A |
| TEST-04, HACS-01 | PASS | 지원 최소 2025.12.0 유지(hacs.json). CI [`minimum-ha`](https://github.com/eigger/hass-ble-esl/actions/runs/39075066369): Py3.13/HA 2025.12.0/plugin 0.13.298 통과, `current`: Py3.14/HA 2026.10.0/plugin 0.13.371 통과(expected-ha-version 검사 포함). 로컬도 1097 passed |
| TEST-05, DEP-02, DEP-05 | PASS | CI [`current / minimum`](https://github.com/eigger/hass-ble-esl/actions/runs/39075066369): manifest 하한(blesession 0.9.0, imagespec 1.1.0) 정확 설치 후 HA 2026.10.0 테스트 통과. 로컬 1097 passed, 3 skipped(test_design_templates의 automation 없음 케이스) |
| DEP-01, DEP-06 | PASS | runtime은 manifest requirements — 직접 import하는 `sensor-state-data>=2.20.0`·`bluetooth-sensor-state-data>=1.9.0` 누락을 감사에서 발견해 #247에서 추가(이전 PASS 기록은 오류였음). 테스트/린트 requirements 분리. main ff12320 [Tests](https://github.com/eigger/hass-ble-esl/actions/runs/39096548266) 성공 |
| DEP-07, CI-06 | PASS | 공통 python-environment action이 manifest·HA component(bluetooth usb recorder diagnostics frontend panel_custom websocket_api) 요구사항을 설치하고 `pip check`를 실행(install.py:132), 위 CI job 모두 통과 |
| HACS-02 | PASS | 루트 README/LICENSE/hacs.json 존재 |
| HACS-03, HACS-05 | PASS | [validate / hacs·hassfest](https://github.com/eigger/hass-ble-esl/actions/runs/39075066366) 통과, ignore 없음 |
| CI-01…CI-05, CI-07, CI-08, CI-12 | PASS | caller가 PR·main push·dispatch(+validate schedule), contents:read, concurrency, 공통 workflow full SHA(`f0ce06b`) 호출, validate에 central template compliance(`check-standards`) 추가, `ha` profile 필수 테스트, lint/test 병렬 |
| CI-09, CI-10, DEP-03, DEP-04 | PASS | updater가 선택 package(imagespec, blesession)의 연산자/extras를 보존하고 기본 브랜치 기준으로 동작. workflow_dispatch dry-run [https://github.com/eigger/hass-ble-esl/actions/runs/39078603182](https://github.com/eigger/hass-ble-esl/actions/runs/39078603182) 성공 — blesession 0.9.0·imagespec 1.1.0이 이미 PyPI 최신이라 PR 없음. 새 하한이 생기는 실제 PR 경로는 아직 미관찰 |
| DOC-01, DOC-06 | PASS | README를 공통 표준 템플릿(header, badges, support, related-projects, license 관리 마커)에 맞춰 동기화, 본문 보존, `check_integration.py` 검증 통과 |
| DOC-02 | PASS | README 영/한 상호 링크·동일 정책 유지 |
| DOC-03, DOC-04, DOC-05 | PASS | `sync_badges.py --check` 통과, Usage 포함, Release 배지(실제 v1.3.0 릴리스 존재) |
| DOC-07 | PASS | `docs/troubleshooting.md` 및 `docs/troubleshooting.ko.md`를 표준 5개 H2 헤딩 및 4열 증상 표로 정비, blesession 공통 문제 해결/프록시 가이드 링크, README 상호 링크 완비, `check_integration.py` 검증 통과 |
| HACS-04, REL-01…REL-03, CI-11 | N/A | 이번 작업은 릴리스·태그를 만들지 않음 |
| REL-04 | N/A | 이전/중단 리포 아님 |

## 남은 작업

예외 외 필수 TODO 없음. 브랜치 보호/required checks를 도입하면 현재 job 이름(`current / …`, `minimum-ha / …`, `validate / …`, `editor`)을 사용합니다. 예외의 재검토 조건은 STANDARDS.md 참조.

## 중앙 현황표 반영 내용 (2026-10-18 반영, hass-repo-standards `e83700c`)

`hass-ble-esl / main`: 진행 중 — 기준 SHA 7acd9ca, 적용: CI 공통화·tests/components 이관·STANDARDS/체크리스트·배지, 최소 HA 2025.12.0 유지+최소 환경 CI 추가, 원격 CI 통과(run 39075066369). 남은 일: required checks 갱신·dependency-update dry-run·중앙 표 갱신·HA 재감사.
