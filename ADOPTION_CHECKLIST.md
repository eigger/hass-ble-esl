# 공통 규칙 적용 체크리스트

## 2026-10-21 재검토

이번 검토 대상은 main `b63733b`에서 시작한 로컬 변경이며, 검토 표준은 `0ec31111a81b0ee5702f1d8a17f03616a10a5db6`입니다. 아래 2026-10-18 채택 표는 이력으로 보존하며 이번 변경의 검증 결과와 구분합니다.

| 항목 | 상태 | 이번 검토 근거 |
|---|---|---|
| GOV-01, GOV-02 | PASS | 최신 원격 main full SHA 확인, 깨끗한 검토 checkout, STANDARDS.md 기준 SHA 기록 |
| GOV-03 | PASS | CHANGELOG Unreleased에 공통 기준·문서·CI·categories 변경 영향 기록 |
| GOV-04 | TODO | 최신 중앙 현황표의 해당 행을 별도 로컬 checkout `artifacts/standards-status-20261021`에서 갱신. 기존 중앙 checkout의 사용자 변경 보존. 중앙 원격 미반영 |
| GOV-05 | PASS | 구현 implement_docs/implement_contract와 독립 review_verify 분리. README 제목 부분 일치 교체 오류를 독립 리뷰에서 발견해 복구하고 재검사. 테스트 기존 482함수 AST 보존도 독립 확인 |
| HACS-03 | PASS | [공식 기본 목록](https://github.com/hacs/default/blob/master/integration)에 `eigger/hass-ble-esl` 포함, 2026-10-21 확인 |
| HACS-01, TEST-04 | PASS | 최소 지원 HA 2025.12.0, current HA 2026.10.1 유지. 정확한 두 환경에서 실제 통합 로딩·payload 계약·전체 회귀 통과 |
| HA-02 | PASS | 실제 전자종이 정보 표시 용도로 `productivity_information` 선택. 공식 Core taxonomy 확인, 근거를 metadata/STANDARDS에 기록. 독립 리뷰에서 제품 목적과 일치 확인 |
| DOC-01…DOC-07, TEST-08 | PASS | 중앙 README·설치 배지·Bluetooth 문서와 테스트 구조 검사 통과. 양언어 제목·본문·기기별 상세 보존을 독립 대조. 기존 482개 테스트 함수 보존, 중앙 collector 1개 추가 |
| DOC-08 | PASS | 예제 2개를 각 current·정확한 하한·최소 HA 환경에서 실제 entry/service schema·repair_yaml11_keys·production render_image 및 설치된 imagespec API로 검증. 아래 환경 표와 로그 참조 |
| CI-01…CI-12 | TODO | 공용 SHA/standards-ref·기존 이벤트·브라우저 job 보존, actionlint 1.7.12 및 중앙 checker 통과. 이번 변경 원격 CI·updater 실제 PR 실행 미검증 |
| HACS-05 | TODO | 이번 변경의 원격 HACS/Hassfest 미실행. 과거 run을 재사용하지 않음 |
| REL-01…REL-03 | N/A | 이번 작업에서 버전·태그·릴리스를 생성하지 않음 |

중앙 원본 자체는 `python -X utf8 artifacts/standards-20261021/scripts/check_repository.py`로 검사하여 `Checked 37 documents, 7 workflows, JSON and caller input contracts`를 확인했습니다. 대상 통합의 실제 실행 결과는 아래에 기록합니다. Windows clone의 CRLF로 인한 원본 렌더러 검사 오류는 깨끗한 검토 checkout을 HEAD blob과 같은 LF로 복원한 뒤 재검증했습니다. 대상에는 `.gitattributes`로 양언어 README·중앙 conftest·payload scaffold 네 파일만 LF를 고정했습니다.

### 이번 검증 환경과 결과

| 환경 | 실제 Python / HA / 테스트 plugin | 실제 imagespec / blesession | payload | 일반 회귀 |
|---|---|---|---|---|
| current | 3.14.7 / 2026.10.1 / 0.13.372 | 1.1.0 / 0.9.0 | 2 passed | 1143 passed, 3 skipped (109.02s) |
| current, 정확한 라이브러리 하한 | 3.14.7 / 2026.10.1 / 0.13.372 | 1.1.0 / 0.9.0 | 2 passed | 1143 passed, 3 skipped (109.19s) |
| 최소 HA | 3.13.15 / 2025.12.0 / 0.13.298 | 1.1.0 / 0.9.0 | 2 passed | 1143 passed, 3 skipped (45.07s) |

- 독립 검증은 WSL Ubuntu의 분리 환경 `/home/eigger/hass-ble-esl-review-20261021/{current,current-min,min-ha}`에서 수행했습니다. 중앙 `actions/python-environment/install.py`를 사용하며 설치 호출만 uv resolver로 연결한 재현 스크립트와 명령 결과는 `artifacts/review-20261021/`에 있습니다. 각 환경의 실제 HA/plugin/하한 assertion과 `pip check` 통과를 확인했습니다. 패키지를 검증 후 덮어 설치하지 않았습니다.
- 최소 HA의 `lru-dict==1.3.0` C 확장 빌드에는 격리 Zig 컴파일러와 해당 링커가 지원하지 않는 `--exclude-libs,ALL`만 제거하는 빌드 wrapper를 사용했습니다. Python/HA/라이브러리 지원 선언이나 패키지 소스는 바꾸지 않았습니다. Windows/WSL 임시 경로 및 네이티브 빌드 실패 로그도 보존했습니다.
- `python -m ruff check .`, `python -m ruff format --check .`(157 files)는 선언된 Ruff 0.17.1 격리 환경에서 재검증했습니다. actionlint 1.7.12의 전체 workflow 문법 검사, `check_integration.py .`, `sync_badges.py . --check`, `git diff --check`도 통과했습니다. README 손상 수정 후 다시 검사했습니다.
- 실행 명령은 WSL의 저장소 루트에서 `/home/eigger/hass-ble-esl-review-20261021/MODE/bin/python artifacts/review-20261021/run_verify.py MODE`이며 MODE는 `current`, `current-min`, `min-ha`입니다. runner는 중앙 `run_payload_contract.py` 통과 후 `python -m pytest tests/components/ble_esl/ -v --timeout 120 --ignore=tests/components/ble_esl/test_payload_examples.py`를 실행합니다. 독립 보고는 `artifacts/review-20261021/REVIEW.md`, 환경별 `home-setup.log`·`verify.log`·`payload.log`·`regression.log`에 있습니다. 이 로그는 로컬 artifacts이며 Git에 포함하지 않았습니다.
- 세 skip은 기존 `color_check`, `message`, `wifi` 디자인 템플릿에 automation이 없는 케이스입니다. 새 payload 예제는 skip 없이 모두 통과했습니다. current resolver 결과와 정확한 하한의 실제 설치값이 같지만 두 환경을 각각 검증했습니다.
- 실제 장치·HA UI·브라우저 테스트·Docker 기반 HACS/Hassfest는 이번에 실행하지 않았습니다. 공용 CI의 해당 job과 기존 브라우저 job은 보존했습니다. 중앙 현황은 로컬 초안만 갱신했으며 원격에 반영하지 않았습니다. 아래 과거 HA-01/08·HA-10·HA-11·HA-13 예외는 별도 동작 변경 없이 유지하며, 이번 작업은 통합 전체의 새 품질 인증이 아닙니다.

## 이전 채택 기록 (2026-10-18)

[사용법과 판정 기준](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/checklist.md). 상태: `TODO` 미확인·미충족 / `PASS` 근거로 확인 / `EXCEPTION` / `N/A`. 원격 CI는 아직 실행되지 않았으므로 CI에 의존하는 항목은 `TODO`입니다.

## 검토 대상

| 항목 | 값 |
|---|---|
| 통합 리포 / 기본 브랜치 | eigger/hass-ble-esl / `main` |
| domain / 구현 경로 | `ble_esl` / `custom_components/ble_esl/` |
| 검토 대상 통합 커밋 / 채택 PR | `ff12320` (main) / [#242](https://github.com/eigger/hass-ble-esl/pull/242) |
| 검토한 표준 전체 SHA | `7acd9cab6ac774e4695f2c962e3d88b5faa4620d` (STANDARDS.md와 일치) |
| 검토일 / 조율 | 2026-10-18 / 주 에이전트 |
| 구현 / 독립 리뷰 | 주 에이전트(사용자 지시) / Opus 서브 에이전트 — 지적 사항은 항목 표의 GOV-05 행 참조 |
| 중앙 현황표 반영 | 2026-10-18 (`e83700c`) |
| 변경 전 지원 최소 HA | 2025.12.0 (`hacs.json`) |
| 유지·변경 지원 최소 | 2025.12.0 유지(상향 시도 후 사용자 요청으로 복원) |
| current 테스트 / 최소 테스트 | Py 3.14 / HA 2026.10.1 / plugin 0.13.372 ; Py 3.13 / HA 2025.12.0 / plugin 0.13.298 |
| 이전 검토 기록 | 최초 검토 |
| 채택 판정 | **예외가 있는 채택** (필수 TODO 없음, EXCEPTION: HA-01/08·HA-10·HA-11·HA-13 일부, GOV-05) |

## 항목

| 규칙 ID | 상태 | 근거 / 남은 작업 |
|---|---|---|
| GOV-01, GOV-02 | PASS | STANDARDS.md 작성, workflow는 `@7acd9ca…` 전체 SHA 고정, editor job의 외부 action도 full SHA |
| GOV-03 | PASS | 채택 PR [#242](https://github.com/eigger/hass-ble-esl/pull/242)에서 영향(워크플로 이름·schedule·bot 브랜치 변경)을 본문과 CHANGELOG에 기록 |
| GOV-04 | PASS | 중앙 표의 hass-ble-esl 행을 2026-10-18 갱신(hass-repo-standards `e83700c`), 다른 행은 변경하지 않음 |
| GOV-05 | EXCEPTION | 초기 CI·구조 이관은 주 에이전트가 직접 구현(사용자 지시), 감사 수정·README 재편은 구현 서브 에이전트가 수행하고 별도 Opus 에이전트가 독립 리뷰, 독립 리뷰는 Opus 서브 에이전트. STANDARDS.md 예외 참조. 리뷰 지적(최소 환경 주장 오류, imagespec 하한, 상태값, 옛 경로)은 수정함 |
| HA-01…HA-13 | EXCEPTION | 2026-10-18 독립 감사(Opus, 읽기 전용) 후 [#247](https://github.com/eigger/hass-ble-esl/pull/247)로 수정·독립 리뷰. 수정: HA-02 `integration_type`, HA-06 PNG executor·취소 전파, HA-07 폴링 제거, HA-08 Failure Count `total_increasing`, HA-09 connectable 목록, HA-10 비공개 `imagespec.schema` import 제거, HA-11 서비스 스키마 검증, HA-12 diagnostics MAC 마스킹·재시도 로그. 미해결은 STANDARDS.md 예외(HA-01/08 unique_id 8자리, HA-13 write-lock RestoreEntity, HA-11 서비스 오류 번역, HA-10 `imagespec.spec.UNSET`). reauth/reconfigure/migration은 N/A(태그 인증 없음, 모델은 options, 데이터 형식 변경 없음) |
| TEST-08 | PASS | `tests/components/ble_esl/` (+`__init__.py` 계층), pytest.ini `testpaths` 일치. 루트 `tests/conftest.py`(설명용 최소 파일)와 domain conftest에 fixture 배치 |
| TEST-02, TEST-03, TEST-09 | PASS | `tests/components/ble_esl/conftest.py`가 `hass`·`enable_custom_integrations`·`MockConfigEntry` 사용, `setup_entry`가 `hass.config_entries.async_setup` 실행 |
| TEST-01, TEST-06, TEST-07 | PASS | 실제 HA fixture 기반 config flow·setup/unload/reload·서비스 회귀 테스트 존재, #247에서 diagnostics 마스킹·재시도 로그·스키마·취소·패널 롤백 회귀 추가(구 코드에서 실패 확인). migration 테스트는 migration이 없어 N/A |
| TEST-04, HACS-01 | PASS | 지원 최소 2025.12.0 유지(hacs.json). CI [`minimum-ha`](https://github.com/eigger/hass-ble-esl/actions/runs/39075066369): Py3.13/HA 2025.12.0/plugin 0.13.298 통과, `current`: Py3.14/HA 2026.10.0/plugin 0.13.371 통과(expected-ha-version 검사 포함). 로컬도 1097 passed |
| TEST-05, DEP-02, DEP-05 | PASS | CI [`current / minimum`](https://github.com/eigger/hass-ble-esl/actions/runs/39075066369): manifest 하한(blesession 0.9.0, imagespec 1.1.0) 정확 설치 후 HA 2026.10.0 테스트 통과. 로컬 1097 passed, 3 skipped(test_design_templates의 automation 없음 케이스) |
| DEP-01, DEP-06 | PASS | runtime은 manifest requirements — 직접 import하는 `sensor-state-data>=2.20.0`·`bluetooth-sensor-state-data>=1.9.0` 누락을 감사에서 발견해 #247에서 추가(이전 PASS 기록은 오류였음). 테스트/린트 requirements 분리. main ff12320 [Tests](https://github.com/eigger/hass-ble-esl/actions/runs/39096548266) 성공 |
| DEP-07, CI-06 | PASS | 공통 python-environment action이 manifest·HA component(bluetooth usb recorder diagnostics frontend panel_custom websocket_api) 요구사항을 설치하고 `pip check`를 실행(install.py:132), 위 CI job 모두 통과 |
| HACS-02 | PASS | 루트 README/LICENSE/hacs.json 존재 |
| HACS-03, HACS-05 | PASS | [validate / hacs·hassfest](https://github.com/eigger/hass-ble-esl/actions/runs/39075066366) 통과, ignore 없음 |
| CI-01…CI-05, CI-07, CI-08, CI-12 | PASS | caller가 PR·main push·dispatch(+validate schedule), contents:read, concurrency, 공통 workflow full SHA 호출, `ha` profile 필수 테스트, lint/test 병렬. main 763c323 [Tests](https://github.com/eigger/hass-ble-esl/actions/runs/39078324708)·[Validate](https://github.com/eigger/hass-ble-esl/actions/runs/39078324723) 성공. main에는 보호규칙·ruleset이 없어 갱신할 required checks 없음(CI-04 해당 변경 없음) |
| CI-09, CI-10, DEP-03, DEP-04 | PASS | updater가 선택 package(imagespec, blesession)의 연산자/extras를 보존하고 기본 브랜치 기준으로 동작. workflow_dispatch dry-run [https://github.com/eigger/hass-ble-esl/actions/runs/39078603182](https://github.com/eigger/hass-ble-esl/actions/runs/39078603182) 성공 — blesession 0.9.0·imagespec 1.1.0이 이미 PyPI 최신이라 PR 없음. 새 하한이 생기는 실제 PR 경로는 아직 미관찰 |
| DOC-01, DOC-06 | PASS | [#246](https://github.com/eigger/hass-ble-esl/pull/246): README를 소개·지원 기기·요구사항·설치·빠른 시작·제한·문서 목록·지원/라이선스 순의 시작 페이지로 재편, 상세는 docs/usage.md·docs/bluetooth.md로 이동(삭제 없음), 영/한 대응, 링크 검사 통과. Issues·Discussions 활성은 이전에 `gh repo view`로 확인 |
| DOC-02 | PASS | README 영/한 상호 링크·동일 정책 유지 |
| DOC-03, DOC-04, DOC-05 | PASS | `sync_badges.py --check` 통과, Usage 포함, Release 배지(실제 v1.3.0 릴리스 존재) |
| DOC-07 | PASS | README 영/한 Bluetooth 절에서 공통 가이드(영어·한국어판) 링크, docs/troubleshooting.md(영/한)에 발견 vs GATT 연결, 프로토콜별 인증·타 앱·전송 조건(미확인은 미확인으로 명시), 진단 항목, 민감정보 제거 안내. 실물 기기 검증은 수행하지 않음 |
| HACS-04, REL-01…REL-03, CI-11 | N/A | 이번 작업은 릴리스·태그를 만들지 않음 |
| REL-04 | N/A | 이전/중단 리포 아님 |

## 남은 작업

예외 외 필수 TODO 없음. 브랜치 보호/required checks를 도입하면 현재 job 이름(`current / …`, `minimum-ha / …`, `validate / …`, `editor`)을 사용합니다. 예외의 재검토 조건은 STANDARDS.md 참조.

## 중앙 현황표 반영 내용 (2026-10-18 반영, hass-repo-standards `e83700c`)

`hass-ble-esl / main`: 진행 중 — 기준 SHA 7acd9ca, 적용: CI 공통화·tests/components 이관·STANDARDS/체크리스트·배지, 최소 HA 2025.12.0 유지+최소 환경 CI 추가, 원격 CI 통과(run 39075066369). 남은 일: required checks 갱신·dependency-update dry-run·중앙 표 갱신·HA 재감사.
