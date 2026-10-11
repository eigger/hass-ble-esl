# imagespec_designer 공용화 작업 계획

작성일: 2026-10-09. 현재 상태는 계획 수립이며 구현·저장소 생성·패키지 배포는 진행하지 않았다.

## 목표와 범위

BLE ESL의 디자이너를 `imagespec_designer`로 추출해 BLE ESL과 Niimbot에서 함께 사용한다. 편집기 기능의 수정 원본을 하나로 만들고, 기기 관리와 실행 정책은 각 통합이 소유한다.

- 저장소 및 Python 배포명: `imagespec-designer` (사용 가능 여부는 저장소/배포 준비 때 확인).
- Python import: `imagespec_designer`.
- `imagespec`: 기존 payload 검증과 렌더링 유지.
- 공용 패키지: 편집 모델, UI, payload 변환, 가져오기/내보내기, 편집용 템플릿과 HA 평가 보조 기능.
- BLE ESL / Niimbot: 매니저, 패널, 기기 조회, 저장, WS 연결, 렌더 환경, 출력 옵션, 서비스 호출, 자동화 설정 읽기/쓰기.

1차 목표는 별도 범용 앱을 만드는 것이 아니라 두 통합이 실제로 사용하는 편집기를 공유하는 것이다. 매니저 프레임워크, BLE 프로토콜 통합, 독립 웹 앱, 별도 npm 배포, 자동화 동작 변경은 범위에 넣지 않는다.

## 소유권과 패키지 구조

| 기능 | 소유 위치 | 연결 방식 |
|---|---|---|
| 캔버스·선택·드래그·속성·레이어·undo | 공용 frontend | 편집 문서와 canvas profile 입력 |
| geometry·문서 검증·payload 변환 | 공용 core | HA/DevicePreset 없이 사용 |
| YAML 가져오기·내보내기 | 공용 core + UI | payload는 공용, 서비스 액션 wrapper는 통합 생성 |
| 센서·Jinja·날씨·의존 엔티티 평가 | 공용 ha 보조 모듈 | HA 호스트가 호출, 평가 결과를 core에 전달 |
| 레이어 이미지·픽셀 비교 | 공용 렌더 보조 모듈 | 통합의 렌더 callback 사용 |
| 편집기 번역·대화상자·기본 템플릿 | 공용 패키지 | 서비스 문구와 폰트 URL은 설정 주입 |
| 카드·필터·상태·별칭·자동화 목록 | 각 매니저 | 기존 레지스트리 및 엔티티 사용 |
| Store·사용자 템플릿 파일·WS·패널 | 각 통합 | 공용 편집 기능으로 요청 전달 |
| 자동화 액션 매칭·생성·저장 | 각 통합 | 공용 payload 사용, 현재 안전 검사 유지 |
| 실제 전송·인쇄 | 각 통합 | 기존 서비스/작업 처리 경로 재사용 |

```text
imagespec-designer/
  src/imagespec_designer/
    core/       # 문서, geometry, specs, compiler, YAML, template model
    ha/         # Jinja/센서/날씨 평가 보조; 필요한 경우에만 import
    rendering/  # 렌더 callback 기반 레이어/비교
    frontend/   # editor/model/dialogs/locales/icons
    templates/  # 공용 기본 디자인
  tests/

hass-ble-esl/.../designer/  # 기존 매니저 + HA 호스트/연결 코드
hass-niimbot/.../designer/  # Niimbot 매니저 + HA 호스트/연결 코드
```

`core`에서 `homeassistant`, `ble_esl`, `niimbot`을 import하지 않는다. 공용 패키지 설치가 `homeassistant` 전체 설치를 요구하지 않도록 한다. HA 연동 코드의 완전한 범용화보다 기존 센서·Jinja 동작을 보존하는 것을 우선한다.

## 먼저 정할 연결 계약

1. **CanvasProfile:** width, height, 명시적인 palette 배열, default font, 글꼴 목록/URL. 출력 회전은 별도 설정으로 전달하고 편집 좌표는 원본 canvas 기준으로 유지한다.
2. **EditorHost:** preview, save, export, import, template 요청을 보내는 연결과 완료/오류 응답. 기존 WS 응답 형식은 가능한 한 유지하고 공용 UI 안의 도메인 하드코딩만 제거한다.
3. **UI 동작:** `저장`, `전송/인쇄`, `자동화 생성`, `자동화에 저장`은 이벤트 또는 host callback으로 전달한다. 공용 UI가 특정 HA 서비스를 직접 선택하지 않는다.
4. **렌더 입력:** 평가된 payload, canvas/output 설정, 배경을 한 묶음으로 전달한다. 통합이 기존 렌더러로 그림을 만들고 공용 코드는 같은 callback으로 레이어와 비교 이미지를 만든다.
5. **편집 상태:** document, dirty, undo, preview variables, 자동화 편집 전 상태 복원을 정의한다. 외부 매니저가 공용 편집기의 DOM이나 내부 필드를 직접 수정하는 연결을 줄인다.

문서 v2 migration은 공용화의 선행 조건으로 만들지 않는다. ESL 문서 v1과 저장 키는 먼저 유지하고, 기기 canvas 정보는 별도 profile로 제공한다. Niimbot 저장은 편집 문서와 canvas/output 설정을 감싸는 통합별 레코드로 시작한다. 공용 문서 자체를 바꿔야 하는 요구가 확인되면 별도 migration 작업으로 분리한다.

## 단계별 작업

### 1. 기존 동작과 연결 계약 확정

- `panel.js`와 각 dialog의 ESL 하드코딩, fonts URL, WS 호출, 매니저의 편집기 내부 접근을 목록화한다.
- `layout.py`, `specs.py`, `importer.py`, `rendering.py`, `export.py`, `design_templates.py`에서 순수 변환과 HA 조회/평가를 나눈다.
- 현재 테스트에서 사용할 대표 문서를 고른다: 센서, Jinja, 다각형, 이미지, 코드, sensor template, 자동화 preview variables.
- CanvasProfile/EditorHost 계약과 오류·비동기 요청 취소·편집 상태 보존 규칙을 문서화한다.

완료 조건: 모든 기존 편집 기능에 소유 위치가 정해지고, 이동 전 payload/픽셀/문서 호환성을 비교할 기준이 확보된다. 새 테스트는 기존 테스트로 확인할 수 없는 경계에만 추가한다.

### 2. BLE ESL 내부에서 편집기 경계 분리

- `panel.js`를 설정과 host 연결을 받는 편집기로 바꾸고 palette·서비스 문구·폰트 경로를 주입한다.
- `manager.js`, `manager.py`는 BLE ESL에 유지한다. 현재 기능과 자동화 저장 검사는 보존한다.
- Python 변환 함수가 `DevicePreset` 대신 canvas/palette 정보를 사용하도록 바꾼다.
- Jinja/센서/날씨 평가를 core와 분리하되 기능 축소 없이 기존 렌더 경로와 연결한다.
- ESL의 `cancel_pending_write` 등 저장 부수 동작은 통합 호스트에 남긴다.

완료 조건: ESL 디자이너가 주입된 연결만으로 동작하고, 기존 저장·preview·전송·자동화 편집·undo·언어 변경 회귀 테스트를 통과한다. 외부 패키지 전환 전에 기능 동등성을 확인한다.

### 3. imagespec-designer 저장소와 배포 패키지 구성

- 분리된 core/ha/rendering/frontend와 편집용 번역·템플릿을 이동한다. 매니저 코드와 상태 문구는 통합에 남긴다.
- JS/JSON/YAML 자산을 wheel에 포함하고 설치된 패키지에서 자산 경로를 얻는 작은 API를 제공한다.
- 기존 코드와 포함 자산의 라이선스·NOTICE를 확인하고 출처를 보존한다.
- 공용 Python 테스트, 브라우저 데모/Playwright 테스트, wheel 설치 검사를 구성한다.
- 공용 custom element 이름을 정하고 동일 버전 자산을 canonical URL로 한 번 로드한다. 등록 guard와 인스턴스별 host 설정을 적용한다.
- Python/HA/imagespec 지원 범위와 공용 API 버전을 정한다.

완료 조건: 새 환경에 wheel을 설치하면 코드와 모든 편집 자산이 동작하며, core 테스트는 HA 없이 실행된다. 아직 외부 게시 없이 로컬 패키지로 검증할 수 있다.

### 4. BLE ESL을 첫 소비자로 전환

- BLE ESL 호스트가 설치된 패키지 함수를 사용하고 공용 frontend URL을 등록하도록 연결한다.
- 기존 매니저가 공용 editor element를 생성하고 CanvasProfile/EditorHost를 전달한다.
- 기존 Store 키, 사용자 템플릿 경로, WS namespace, 서비스 payload를 유지한다.
- 사용을 전환한 편집기 중복 소스를 제거한다. 필요하면 기존 진입 경로에 얇은 호환 wrapper만 둔다.
- 기존 자동화 편집은 payload만 수정하고 배경 제한·최신 액션 확인·모호한 대상 차단을 유지한다.

완료 조건: ESL이 공용 패키지만으로 기존 편집 기능을 제공한다. 대표 문서의 렌더 픽셀과 export가 동등하며, 기존 저장 데이터를 그대로 읽는다.

### 5. Niimbot 매니저와 디자이너 연결

- Niimbot 전용 매니저에 프린터 목록·상태·편집 진입을 구현한다. ESL 동기화 상태를 필수 기능으로 넣지 않는다.
- 통합별 저장소·WS·패널 호스트를 만들고 필요한 HA dependencies를 선언한다.
- 캔버스 크기는 명시적 저장/입력 값 → cloud label 값 → 기존 기본값 순으로 해석한다. 현재 용지 변경이 저장 디자인을 자동 변경하지 않게 한다.
- 회전·density·label_type·copies는 Niimbot 호스트에서 관리하고 모델별 기존 검증을 사용한다.
- 편집 preview는 렌더 함수를 직접 호출해 BLE 실행과 이미지 coordinator 변경을 피한다. 인쇄 버튼은 기존 실제 인쇄 경로에 연결한다.
- 이미지 카드는 현재 `last_label_made`의 의미를 반영한다. 실제 성공 이미지 추가는 필요할 때 별도 변경으로 다룬다.
- 저장, template, YAML export 및 신규 자동화 생성 후 기존 자동화 편집을 연결한다. 명시적 대상 액션부터 지원하고 기존 옵션은 보존한다.

완료 조건: Niimbot에 복제된 편집기 구현 없이 편집·저장·preview·인쇄·YAML·자동화 작업이 가능하다. 편집 preview와 실제 서비스 렌더 입력 및 회전 후 결과가 일치한다.

### 6. 동시 설치 검증과 릴리스

- 두 패널을 번갈아 열어 문서·폰트·언어·연결·undo가 인스턴스별로 유지되는지 확인한다.
- WS/Store 분리, custom element 중복 등록, 한 통합 unload 후 다른 통합 동작을 검증한다.
- 공용 자산은 HA 인스턴스당 한 번 등록하고 HA 종료까지 유지한다. 도메인별 host와 패널만 독립적으로 해제한다.
- 두 통합이 같은 Python 패키지를 사용하므로 호환 가능한 릴리스 조합과 의존성 정책을 정한다. 서로 다른 버전을 독립 설치하는 방식을 전제하지 않는다.
- 공용 패키지 릴리스 후보로 양쪽을 테스트한 뒤 라이브러리 → ESL → Niimbot 순으로 배포한다.
- 설치·업그레이드·지원 버전과 회귀 시 되돌리는 절차를 문서화한다.

완료 조건: 단독 설치/동시 설치, 재시작/unload, 한국어/모바일, 기존 자료 호환성 검증을 모두 통과한다. 지원하는 라이브러리/통합 조합이 명시되어 있다.

## 검증 항목과 변경 묶음

| 변경 묶음 | 주요 검증 |
|---|---|
| ESL 내부 경계 분리 | 기존 Python·Playwright 테스트, 대표 문서 payload와 픽셀 비교 |
| 패키지 추출 | core의 HA 비의존성, wheel 자산 포함, 공용 editor 테스트 |
| ESL 패키지 전환 | 기존 Store·사용자 템플릿·자동화 보존, UI 동등성 |
| Niimbot 기본 이식 | 크기/cloud fallback, 0/90/180/270도 회전, preview 무부작용, 출력 옵션 검증 |
| Niimbot 자동화 연결 | payload만 변경, 인쇄 옵션/다른 액션 보존, 동시 수정·모호한 대상 처리 |
| 릴리스 준비 | 두 통합 동시 설치, 자산/element 공유, 독립 수명주기, 버전 조합 |

공용 테스트는 편집기 자체를 검증하고 통합별 테스트는 연결과 기기 정책을 검증한다. 실제 Niimbot 인쇄 품질·용지 방향은 기기 smoke test로 확인하며 PNG 비교와 구분해서 기록한다.

첫 실행 작업은 **1단계 계약 확정과 2단계 BLE ESL 내부 분리**다. 이 변경이 검증된 뒤 패키지를 추출한다. 별도 저장소 생성이나 배포부터 시작해 현재 결합을 그대로 이동시키지 않는다.
