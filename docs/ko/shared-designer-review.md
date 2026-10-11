# BLE ESL / Niimbot 공용 디자이너·매니저 검토

검토일: 2026-10-09. 로컬 `hass-ble-esl`, `hass-niimbot`, `imagespec` 소스를 기준으로 한 설계 제안이다. 이 문서는 구현하거나 배포한 결과가 아니다.

> 후속 논의로 범위를 **`imagespec_designer` 편집기 공용화 + 통합별 매니저 유지**로 좁혔다. 아래의 공용 매니저·공용 패널/저장 호스트·문서 v2 제안은 초기 검토안이다. 실제 작업 범위와 순서는 [공용 디자이너 작업 계획](shared-designer-plan.md)을 따른다.

## 권장 방향

별도 저장소의 Python 배포 패키지(가칭 `ha-image-designer`)에 **편집 모델, 프런트엔드 자산, HA 연동 공통 기능**을 모으고, 각 통합에는 **기기 어댑터와 기존 전송 서비스**를 남긴다. 프런트엔드 JS·번역·기본 디자인 YAML을 wheel에 포함하면 별도 프런트엔드 설치 없이 두 통합에서 같은 패키지를 사용할 수 있다.

`imagespec`은 지금처럼 그림을 그리는 라이브러리로 유지한다. 디자이너를 그 안에 넣으면 렌더러가 HA 상태·저장소·자동화·UI 수명주기까지 책임져야 하므로, 별도 패키지가 적합하다. 당장은 하나의 배포 패키지 안에 `core`, `ha`, `frontend` 경계를 두고, 다른 플랫폼에서 실제 사용하게 될 때 배포 단위 분리를 검토한다.

별도 HACS 공용 통합을 필수 설치하게 만드는 방식보다, 두 통합의 `manifest.json` requirements로 라이브러리를 설치하는 방식이 사용자 설치 절차가 간단하다. HA가 requirements에 지정한 Python 패키지를 설치하는 방식은 [공식 manifest 문서](https://developers.home-assistant.io/docs/creating_integration_manifest/)에 설명되어 있다.

## 현재 코드에서 확인한 경계

| 영역 | 현재 상태 | 공용화 방향 |
|---|---|---|
| 렌더러 | 양쪽 manifest가 `imagespec[datamatrix]>=1.0.1` 사용 | imagespec 유지, 렌더 컨텍스트와 출력 설정 전달 |
| 편집 UI | `designer/frontend/panel.js` 약 3,700줄, `manager.js` 약 1,179줄 | 캔버스·속성·레이어·undo·대화상자 공용화, 서비스와 상태 의미 주입 |
| 편집 문서 | `layout.py`, `specs.py`, `importer.py` | geometry/문서 검증·payload 변환과 HA 템플릿 평가 분리 |
| 디자이너 서버 | `designer/__init__.py`에 저장·미리보기·WS·패널·ESL 전송 결합 | 공용 HA 호스트 + BLE ESL 어댑터로 분리 |
| 매니저 | `manager.py`의 레지스트리 조회가 ESL unique ID 규칙 사용 | 연결 자동화 로직은 공용, 엔티티 매핑은 어댑터 |
| 자동화 액션 | Python `export.py`, JS `manager.js`가 `ble_esl.write`를 직접 사용 | action 생성·검색·가져오기·수정 정책을 서비스 계약으로 추출 |
| 색상 | Python과 JS가 `BW/BWR/BWRY` 문자열에서 색상 추론 | 명시적 palette 배열을 전달 |
| 글꼴 | UI의 `/ble_esl_designer_fonts`, 서버의 통합 fonts 경로 | fonts URL·resolver·default font를 어댑터 설정으로 전달 |
| 저장 | `ble_esl.designer`, `ble_esl.sensor_templates`, `ble_esl.automation_links` | 도메인별 저장소 유지, 기존 ESL 키와 자료 보존 |
| 디자인 템플릿 | 기본 YAML과 사용자 `config/ble_esl/templates` | 기본 템플릿은 공용, 사용자 경로는 통합별 설정 |

현재 `layout.py`와 `specs.py`도 HA `Template`을 import한다. 파일만 밖으로 옮기는 것으로는 독립적인 편집 코어가 되지 않는다. Jinja 평가, 센서·날씨 값 조회를 별도 HA 계층으로 이동해야 한다.

## 두 기기의 차이를 드러내는 계약

| 항목 | BLE ESL | Niimbot |
|---|---|---|
| 화면 크기 | 기기 preset으로 결정 | 서비스 입력 → cloud label 크기 → 기본 400×240 |
| 현재 렌더 회전 | renderer의 고정 디스플레이 방식 | `rotate_mode="image"`, 회전 후 이미지 크기가 달라질 수 있음 |
| 렌더 색상 | BW / BWR / BWRY | 현재 render.py는 black/white |
| 실행 액션 | `ble_esl.write` | `niimbot.print` |
| 실행 옵션 | 기존 write 정책 | density, label_type, copies |
| 상태 의미 | 표시 동기화, 최근 성공 전송, 전송 결과 | 용지·덮개·연결·인쇄 진행 등 |
| 이미지 엔티티 | `last_updated_content`: 마지막 성공 전송 | `last_label_made`: 인쇄 시도 전 렌더 및 preview에서도 갱신 |

공용 매니저는 검색·정렬·카드·편집 진입·자동화 연결을 제공하되, `display_in_sync` 같은 ESL 전용 상태를 모든 기기의 필수 항목으로 만들지 않는다. 상태의 이름·유형·엔티티 ID·단위·표시 의미를 어댑터가 제공하고, 지원되는 필터와 버튼만 표시한다. Niimbot 카드에는 현재 이미지 의미에 맞는 문구를 쓰거나, 통합에서 실제 인쇄 성공 이미지/시점을 별도로 기록해야 한다.

Niimbot 디자이너 preview는 기존 `niimbot.print(preview=true)` 호출 대신 렌더 함수를 직접 사용한다. 현재 그 서비스는 preview에서도 이미지 coordinator를 변경한다. 편집 중 미리보기는 저장·출력 상태를 변경하지 않는 경로로 유지하고, 실제 인쇄만 기존 서비스 처리 경로를 재사용한다.

## 제안하는 패키지와 어댑터

```text
ha-image-designer/
  src/ha_image_designer/
    core/       # 편집 문서, 프레임, 검증, payload 변환, YAML, 템플릿 모델
    ha/         # 상태/Jinja/날씨/recorder, Store, WS, 패널, 자동화 연동
    frontend/   # manager/editor/dialogs/model/locales/icons
    templates/  # 공용 기본 디자인

hass-ble-esl/custom_components/ble_esl/designer_adapter.py
hass-niimbot/custom_components/niimbot/designer_adapter.py
```

`core`는 `homeassistant`와 각 통합을 import하지 않는다. `ha` 모듈은 HA 호스트에서만 사용한다. 공용 패키지의 설치 의존성에 `homeassistant` 전체를 넣지 않는다. Python/HA 지원 범위는 양쪽 통합과 현재 imagespec의 범위를 기준으로 명시한다.

최소 어댑터 책임은 다음과 같다. 아래 이름과 자료형은 제안이며 기존 API가 아니다.

```python
class DesignerAdapter(Protocol):
    domain: str
    panel: PanelConfig
    action_contract: ActionContract

    async def list_devices(self) -> list[DeviceDescriptor]: ...
    async def resolve_output(self, entry_id, document) -> OutputProfile: ...
    def render_context(self, profile) -> RenderContext: ...
    async def execute(self, entry_id, payload, profile, options) -> ExecutionResult: ...
```

- `DeviceDescriptor`: entry/device ID, 이름, palette, capabilities, 의미가 정의된 상태 엔티티 매핑.
- `OutputProfile`: 편집 캔버스 크기, 출력 회전 방식, 회전 후 bitmap 크기, palette, 글꼴 설정. BLE 프로토콜의 `DevicePreset`을 공용 API로 노출하지 않는다.
- `ActionContract`: 서비스명, 대상 매칭 정책, service data 생성, 기존 액션에서 출력 설정 읽기, 편집 가능한 필드 목록.
- `ExecutionResult`: 성공/실패/진행 정보를 UI에서 다룰 공통 형태. 실제 BLE 연결·재시도·인쇄 프로토콜은 기존 통합이 책임진다.

Niimbot의 density 범위와 label_type 지원 여부는 모델 메타데이터에서 얻는다. 편집기 검증과 실제 서비스 검증이 같은 함수를 사용하도록 하고, UI에 전체 기종 공통 범위를 하드코딩하지 않는다. 모델 정보가 없는 경우 기존 서비스의 fallback과 일치하는 정책을 표시한다.

프런트엔드는 `hass`, 서버 연결, capabilities와 문구를 주입받는다. 서버 namespace도 `ble_esl/designer`, `niimbot/designer`처럼 통합별로 둔다. 패널마다 별도 호스트 인스턴스를 만들고, 공용 WS 핸들러는 어댑터를 캡처하는 팩토리로 등록한다. 도메인별 Store, 실행 lock, unload 처리와 패널 등록 상태를 분리한다.

## 문서와 자동화 계약

기존 ESL 문서 v1에는 width/height/rotate가 없고 entry preset에 기대고 있다. 새 내부 문서에는 편집 모델과 출력 설정을 분리한다.

```yaml
version: 2
canvas:
  width: 400
  height: 240
background: white
elements: []
output:
  rotate: 0
  options: {}   # Niimbot density/label_type/copies 등; 어댑터 검증
```

실제 palette와 지원 범위는 기기 capabilities가 기준이다. 저장 문서에 기기 capabilities 전체를 복제하지 않는다. 서비스로 내보낼 때는 기존 서비스가 받는 `payload`, `width`, `height`, `rotate` 등의 형태로 변환한다. 디자이너 문서를 자동화 실행의 새 필수 형식으로 만들지 않는다.

ESL v1은 읽기 호환을 유지하고 entry의 현재 preset으로 크기를 해석한다. 저장 형식 변경은 별도 Store 버전과 명시적 migration으로 처리하며 기존 사용자 템플릿 경로를 유지한다. 구버전으로 돌아갈 수 있도록 원본 보존/백업 정책을 둔다. Niimbot의 cloud 용지 변경이 저장 디자인을 자동으로 resize하거나 overwrite하지 않도록, 현재 용지와 저장 캔버스의 차이를 표시하고 사용자가 적용하게 한다.

회전은 편집 좌표와 출력 좌표를 구분한다. 원래 canvas 좌표로 편집하고 최종 회전 이미지를 별도 미리보기로 보여 주면 layer drag 좌표를 회전시키는 복잡도를 줄일 수 있다. 최종 미리보기와 실제 서비스는 동일한 OutputProfile과 렌더 함수를 사용한다. 서비스 옵션을 생략했을 때의 기본값까지 일치시켜야 한다. 프린터 드라이버의 흑백 변환과 모델별 출력 처리도 별도 확인해야 하며, 렌더 PNG 일치가 물리적 출력 품질까지 보장하지는 않는다.

현재 ESL 자동화 편집은 최신 설정을 다시 읽고, 가져온 액션이 유일하게 그대로 남아 있는지 검사한 뒤 `data.payload`만 바꾼다. 배경 변경도 제한한다. 공용화 후에도 이 동작을 유지한다.

Niimbot 1차 이식에서도 기존 자동화는 payload만 수정하고 width/height/rotate/background와 density/label_type/copies는 원본을 보존한다. 가져온 크기·회전 설정을 편집기에 반영하고 이 세션에서는 변경을 제한한다. 이후 옵션 편집을 지원할 때만 명시적인 필드 수정 계약을 추가한다. 신규 자동화 생성은 선택한 크기·회전·인쇄 옵션을 포함할 수 있다.

대상이 없는 Niimbot 액션은 현재 프린터 한 대일 때 실행 가능하지만, 자동화 편집 대상으로 자동 귀속시키면 두 번째 프린터 추가 후 의미가 바뀐다. 직접 device/entity 대상이 있는 액션부터 지원하고, 무대상·템플릿·area/label 등 모호한 대상은 초기 자동 편집 범위에서 제외한다. 수동 연결 기능과 자동화 액션 수정 가능 여부는 따로 다룬다.

## 배포와 동시 설치

Python 코드와 프런트엔드를 같은 wheel 버전으로 배포한다. JS/JSON/YAML을 package data에 포함하고 [setuptools의 package data 지침](https://setuptools.pypa.io/en/stable/userguide/datafiles.html)에 따라 패키지 resource로 접근한다. 설치된 wheel에서 모든 자산이 존재하는지도 검증한다. 개발은 editable install로 양쪽 통합에서 테스트할 수 있고, 실제 배포는 공개 CI와 태그 릴리스를 사용한다.

두 통합은 같은 HA Python 환경을 쓰므로 서로 다른 라이브러리 버전을 각자 독립적으로 쓰는 구조를 전제하면 안 된다. **동일 major의 하위 호환 API와 겹치는 지원 버전 범위**, 양쪽을 함께 설치한 CI, 릴리스 조합표가 필요하다. 정확한 버전 고정이 필요하면 두 통합의 지원 조합을 함께 관리한다. 범위 지정만으로 런타임 호환성이 자동 보장되지는 않는다. 서버/프런트엔드 API 버전도 handshake에서 확인한다.

브라우저의 `customElements` 등록은 전역이다. 현재 `manager.js`와 `panel.js`는 `ble-esl-*` 이름을 등록하므로 경로만 바꿔 두 번 로드하면 충돌할 수 있다. 공용 자산은 `/ha_image_designer/<library-version>/` 같은 **하나의 canonical URL**로 한 번 등록하고, 중립적인 element 이름과 인스턴스별 설정을 쓴다. 같은 클래스에 도메인 설정을 전역으로 저장하지 않는다. 공유 자산 등록은 HA 인스턴스당 한 번, 패널과 호스트 등록은 통합별로 한다. 공용 자산은 한 통합 unload 때문에 다른 패널에서 사라지지 않도록 HA 종료까지 유지한다.

Niimbot manifest에는 현재 디자이너용 `frontend/http/panel_custom/websocket_api` dependencies가 없다. 이식 시 실제 사용하는 HA 컴포넌트를 선언한다. 기존 ESL의 관리자 전용 패널·WS 검사, preview 입력 크기 제한, YAML 제한을 공용화 과정에서도 유지한다.

## 권장 진행 순서와 완료 조건

1. **BLE ESL 안에서 결합부터 해제한다.** 서비스명·palette·폰트 경로·기기 메타데이터·전송을 설정/어댑터로 치환한다. 기존 저장 키·WS 경로·사용자 동작은 유지한다.
2. **공용 저장소와 wheel로 옮긴다.** 공용 코드의 수정 원본을 하나로 만든 뒤 BLE ESL이 패키지를 사용하도록 전환한다. 자산 포장·캐시·수명주기를 확인한다. 수동 복사본을 두 저장소에서 유지하지 않는다.
3. **Niimbot 최소 기능을 이식한다.** 프린터 목록, 용지/캔버스 크기, 공용 편집기, 저장, 부작용 없는 preview, print, YAML export를 제공한다. 기존 서비스에 인쇄를 맡긴다.
4. **자동화와 템플릿을 연결한다.** 공용 연결 목록과 안전한 액션 편집을 사용하고, Niimbot의 크기·회전·옵션 보존 규칙을 검증한다.

검증은 기존 `tests/test_designer*.py`, `test_manager.py`, `tests/frontend/{editor,manager,manager-ux,language,parameters}.spec.js`를 기반으로 이관한다. 테스트를 무조건 복제하기보다 공용 계약 테스트와 통합별 회귀 테스트로 나눈다.

- ESL의 기존 저장 문서·센서 템플릿·수동 자동화 연결을 읽고 기존 export 결과와 렌더 픽셀을 보존한다.
- Niimbot 명시 크기/기본 크기/cloud 크기, 0/90/180/270도 회전에서 편집기 출력과 서비스 렌더 결과가 같다.
- preview는 BLE 실행과 이미지 coordinator 변경을 하지 않는다. 실제 인쇄에서는 기존 서비스 검증과 진행 처리가 유지된다.
- 기존 자동화는 대상·트리거·조건·다른 액션·인쇄 옵션을 보존하고, 동시 수정/중복 액션은 저장을 막는다.
- 두 통합 동시 설치에서 WS·Store·패널·폰트가 섞이지 않고 custom element 중복 등록이 없다. 한 통합 unload 이후에도 다른 통합이 동작한다.
- 한국어·모바일·undo·미저장 입력 유지와 지원 라이브러리 버전 조합을 확인한다.

가장 큰 작업은 Niimbot에 UI를 붙이는 단계보다, 현재 ESL 전용 가정이 퍼져 있는 서버·프런트엔드의 경계를 만드는 단계다. **BLE ESL을 첫 번째 공용 라이브러리 소비자로 먼저 전환한 뒤 Niimbot를 붙이는 순서**를 권장한다. 실제 공용화가 작동하는지를 두 번째 구현을 만들기 전에 확인할 수 있다.
