# 적용한 공통 규칙

- 표준: https://github.com/eigger/hass-repo-standards/tree/v1.1.4
- 참조 커밋 SHA: a90531d05613597632a4c10c11ce1dbc45e0bab6
- Standards release: v1.1.4
- Resolved standards SHA: a90531d05613597632a4c10c11ce1dbc45e0bab6
- 재검토일: 2026-10-21 (대상 main `b63733b`, 로컬 작업 트리)
- 이전 기준 SHA: `7acd9cab6ac774e4695f2c962e3d88b5faa4620d`
- 채택일: 2026-10-18 (채택 PR: #242)
- profile: integration / ha
- 적용 점검표: [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md)
- 중앙 현황표: https://github.com/eigger/hass-repo-standards/blob/main/docs/adoption-status.md
- 조율: Codex root / 구현: implement_docs, implement_contract / 독립 리뷰·검증: review_verify
- 중앙 현황: 최신 중앙 main의 해당 행을 별도 로컬 checkout에 갱신. 원격 반영 전이며 상세는 ADOPTION_CHECKLIST.md 참조
- 실제 기본 브랜치: `main`
- 테스트 경로: `tests/components/ble_esl/` (브라우저 테스트는 `tests/components/ble_esl/frontend/`)
- 변경 전 지원 최소 HA / 선언 근거: 2025.12.0 (`hacs.json`, README 설치 절)
- 적용 후 지원 최소 HA: **2025.12.0 유지** — 중간에 2026.10.0 상향을 시도했으나 사용자가 "가능하면 내리고"라고 해 되돌림. 테스트 헬퍼를 두 버전 호환으로 고쳐 2025.12.0에서 통과함을 확인
- current HA 테스트 환경: Python 3.14 / HA 2026.10.1 / pytest-homeassistant-custom-component 0.13.372
- 최소 HA 검증 환경: Python 3.13 / HA 2025.12.0 / plugin 0.13.298 (`requirements_test_min.txt`, `constraints/homeassistant-min.txt`), CI job `minimum-ha`
- 최소 package 검증: `blesession>=0.9.0`, `imagespec[datamatrix]>=1.1.0` — CI `dependency-modes: minimum`이 정확한 하한 설치

## 2026-10-21 재검토

- README 공통 영역·HACS 설치 배지·Default 상태·HACS Downloads를 중앙 렌더러로 갱신합니다. 등재 근거: [HACS 공식 integration 목록](https://github.com/hacs/default/blob/master/integration), 2026-10-21 `eigger/hass-ble-esl` 포함 확인. Default는 Core 통합이라는 뜻이 아닙니다.
- DOC-07은 같은 언어의 blesession 사용자 원본과 기기별 문제 해결을 연결하며, 기존 한국어 경로도 보존합니다.
- DOC-08은 전체 HA 액션 YAML과 중앙 scaffold, 실제 서비스 스키마·통합 준비·imagespec 렌더링 계약을 추가합니다. Tests와 dependency updater의 `standards-ref`는 위 검토 SHA로 고정합니다.
- HA-02 제품 분류는 `productivity_information`입니다. README의 실제 용도인 달력·날씨·센서 값·사진을 표시하는 전자종이 디스플레이가 근거이며, 보조 센서나 스위치 플랫폼으로 분류하지 않았습니다. 공식 taxonomy는 중앙 snapshot의 Core `ec18d8b25d1ee39aa8b85a72a170e42bee33228c`를 검토했습니다.
- 옵션 flow 클래스 이름은 `BleEslOptionsFlow`로 명확히 하여 중앙 번역 검사가 `options.step.init`으로 인식하도록 했습니다. 옵션 동작·번역 내용·지원 버전은 유지합니다.
- Windows checkout에서도 중앙 관리 파일의 정확한 비교가 유지되도록 `.gitattributes`에서 README 두 개·root conftest·payload scaffold 네 파일만 LF를 고정했습니다.
- 독립 검증에서 current·정확한 라이브러리 하한·최소 HA 세 환경 모두 payload 2 passed, 회귀 1143 passed / 3 skipped를 확인했습니다. Ruff 0.17.1·actionlint·중앙 검사도 통과했습니다. 실제 버전·명령·검증 범위는 ADOPTION_CHECKLIST.md의 재검토 절에 별도로 기록합니다. 아래 과거 예외와 2026-10-18 실행 결과를 새 변경의 통과 근거로 재사용하지 않습니다.
- 과거 GOV-05 위임 예외는 이번 재검토에서 구현/독립 리뷰 담당을 분리하여 해소했습니다. 과거 수행 방식은 아래 이력에 보존합니다. 기존 HA 동작 예외는 유지합니다. 원격 CI·중앙 원격 갱신·실물 기기 검증은 이번에 수행하지 않았습니다.

## 예외

| 규칙 ID | 이유 | 담당자 | 재검토 조건 |
|---|---|---|---|
| GOV-05 | 초기 CI·테스트 구조 이관은 서브 에이전트가 아닌 주 에이전트가 수행(사용자 지시: 작성 후 서브 에이전트 리뷰). 이후 감사 수정·README 재편은 구현 서브 에이전트가, 리뷰는 별도 Opus 에이전트가 수행 | @eigger | 다음 표준 재검토 때 구현도 위임 |
| HA-01, HA-08 | 엔티티 unique ID가 태그 MAC 마지막 8자리만 사용(`ble_esl_{identifier}_{key}`). 첫 2바이트만 다른 두 태그는 충돌 가능. 변경하려면 registry 마이그레이션·entry 버전 증가 필요 | @eigger | 충돌 사례 보고 또는 다음 데이터 형식 변경 시 |
| HA-13 | write-lock 스위치가 RestoreEntity 대신 `entry.data`를 갱신해 상태 보존 | @eigger | 데이터 형식 마이그레이션을 도입할 때 |
| HA-11 | 서비스 오류 메시지가 번역 키가 아닌 영어 문자열(`unknown_protocol`만 번역) | @eigger | 서비스 오류 번역 작업 시 |
| HA-10 | `designer/specs.py`가 공개 export가 없는 `imagespec.spec.UNSET`을 import | @eigger | imagespec가 공개 export를 제공할 때 |

## 2026-10-23 다운로드 배지 부분 갱신

- 배지·DOC-03/05와 Validate 형식 검사기만 중앙 [`b54ac48102d6e326c6929071fdc02ba8fade794e`](https://github.com/eigger/hass-repo-standards/tree/b54ac48102d6e326c6929071fdc02ba8fade794e)를 채택합니다. 이전 기준 SHA `0ec31111a81b0ee5702f1d8a17f03616a10a5db6`의 채택 이력·예외는 보존합니다. 모든 중앙 workflow/action pin과 standards-ref는 GOV-02의 단일 기준 SHA 계약에 맞춰 갱신합니다. 중앙 diff에서 공용 workflow/action 실행 파일은 이전 기준과 동일함을 확인했습니다.
- 대상 기본 브랜치 커밋: `913bab1ba5331faf9d24b7ca6de2b97996aa13a0`. 주 에이전트 직접 구현·자체 리뷰(GOV-05의 배지/생성물 변경 범위), 검증은 [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md#2026-10-23-downloads-배지-부분-검증)에 기록합니다.
- Downloads는 모든 릴리스 첨부 asset 다운로드 합계입니다. 사용자 지시에 따라 ZIP 배포를 도입하지 않으며 현재 HACS 소스 파일 설치는 이 수치에 집계되지 않습니다. 통합 코드·의존성·지원 최소·기존 설치 안내는 변경하지 않습니다.

## 2026-10-23 ZIP 릴리스 배포

- 기준 중앙 SHA: `0c1592977591ecba077a4666d699840062711201` ([중앙 PR15](https://github.com/eigger/hass-repo-standards/pull/15) 스쿼시 머지). 이전 `b54ac48102d6e326c6929071fdc02ba8fade794e` 채택 이력·예외를 보존하며 HACS-04·CI-11의 ZIP 배포 계약을 추가합니다.
- 대상 시작 SHA: `e55125c6cfde578983400d1f4fdd8ef0fb199422`. hacs.json의 zip_release/filename과 중앙 release caller를 함께 적용합니다. archive 파일명은 `ble_esl.zip`, ZIP 루트는 해당 통합 파일입니다.
- 중앙 workflow/action pin과 standards-ref는 단일 SHA로 정합화합니다. release:published에서 기존 해당 릴리스에 ZIP만 첨부하며 소스 버전·태그·릴리스 발행은 자동 변경하지 않습니다. 기존 asset 덮어쓰기를 거부합니다.
- 기존 지원 최소 HA `2025.12.0`와 통합 버전 `1.5.1` 및 의존성·구현은 보존합니다. 기존 태그의 hacs.json은 소급 수정하지 않으므로 다음 릴리스부터 ZIP 설치로 전환됩니다.
- immutable-releases 설정은 enabled=false/enforced_by_owner=false로 확인했습니다. 업로드 지연·실패 및 기존 asset 복구는 중앙 [릴리스 계약](https://github.com/eigger/hass-repo-standards/blob/0c1592977591ecba077a4666d699840062711201/docs/releases.md#zip-릴리스-첨부)을 따릅니다. 실제 새 릴리스 발행·설치·기기 검증은 이번 작업에 포함하지 않습니다.

## 2026-10-25 중앙 검사기 갱신

- 검토한 중앙 main: `1863343638014adb8a4001afc8fddc1a27dc500f` (git ls-remote 확인). 이전 기본 기준 `0c1592977591ecba077a4666d699840062711201`의 채택 이력은 위 기록을 보존합니다.
- 모든 중앙 workflow/action pin과 reusable workflow의 standards-ref를 같은 검토 SHA로 맞춥니다. HACS-04는 actions/*의 full SHA 고정을 유지하면서 SHA 값 차이를 허용합니다.
- 통합 코드·런타임 의존성·지원 최소·배포 버전은 이번 변경 대상이 아닙니다. 기존 채택 범위를 전체 완료로 바꾸지 않으며 실제 검증 결과와 남은 항목은 ADOPTION_CHECKLIST.md의 같은 날짜 기록을 참조합니다.


### 2026-10-25 Standards 파일·표시 이름 분리

- 기존 Validate의 중앙 검사 job을 `standards.yml`로 옮기고 workflow/job 표시 이름을 `Standards`로 줄였습니다. Validate의 HACS/Hassfest, 검사 항목·통과 기준·실행 단계·조건·권한은 유지합니다.
- 위치 인식과 중앙 명명 안내를 맞춘 검토 소스: `ca740d88b32fa5dcbc94c41fce2908450c76ed50` ([중앙 PR #24](https://github.com/eigger/hass-repo-standards/pull/24), 현재 이 PR의 의존 변경). 이전 기준 `1863343638014adb8a4001afc8fddc1a27dc500f`의 검증 이력은 앞 기록으로 보존합니다. 모든 중앙 pin·standards-ref는 같은 새 검토 소스로 맞춥니다.
### 2026-10-25 immutable central release reference migration

- User-requested partial migration: current central caller references use immutable `v1.0.0` resolved to `44349ee5621eea5d80e5c427f7a2435d2c2491bb`. Runtime code, dependencies, support minimum, manifest and integration version are unchanged.
