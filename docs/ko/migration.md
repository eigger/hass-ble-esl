# hass-gicisky에서 마이그레이션

**[English](../migration.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 원문](../migration.md)을 따릅니다.

[`hass-gicisky`](https://github.com/eigger/hass-gicisky)는 보관(archived) 처리되었습니다. `hass-ble-esl`이 그 후속으로, PickSmart(Gicisky) 프로토콜, 페이로드 형식, 옵션, 엔티티가 모두 같습니다. 바뀐 것은 통합구성요소 **도메인**(`gicisky` → `ble_esl`) 하나인데, Home Assistant는 설정 항목을 도메인 사이에서 옮길 수 없어서 태그를 다시 추가하고 액션 이름을 바꿔야 합니다. 페이로드 YAML은 손댈 것이 없습니다.

## 간단 버전

1. **기존 통합구성요소 제거** — **설정 → 기기 및 서비스**에서 Gicisky 기기 항목을 삭제하고, `hass-gicisky`를 제거합니다(HACS → 제거, 또는 `custom_components/gicisky` 삭제).
2. **`hass-ble-esl` 설치** — HACS로 설치하고 Home Assistant를 재시작합니다.
3. **태그 추가** — 예전처럼 자동으로 발견됩니다; 하나씩 확인합니다.
4. **자동화 수정** — `gicisky.write` → `ble_esl.write` (`gicisky.write_guarded` → `ble_esl.write_guarded`)로 바꾸고, 기기 ID가 새로 생겼으니 대상 기기를 다시 선택합니다. 페이로드는 그대로입니다.

대부분은 이걸로 끝입니다. 아래는 각 단계의 상세, 미리 적어 둘 것, 확인 방법입니다.

## 자세한 버전

### 한눈에 보는 변경점

| | `hass-gicisky` | `hass-ble-esl` |
|---|---|---|
| 도메인 / 폴더 | `gicisky` · `custom_components/gicisky` | `ble_esl` · `custom_components/ble_esl` |
| 액션(서비스) | `gicisky.write`, `gicisky.write_guarded` | `ble_esl.write`, `ble_esl.write_guarded` |
| 액션 파라미터 | `payload`, `rotate`, `background`, `dry_run`, `debounce_override_ms` | **동일** |
| 페이로드 형식 | imagespec 요소 목록 | **동일** |
| 기기 이름 | `Gicisky <MAC 뒤 8자리>` | `Gicisky <MAC 뒤 8자리>` (같음) |
| 엔티티 | Battery, Battery Voltage, Signal Strength, Connectivity, Display In Sync, Write Duration, Failure Count, Last Failure Time, Last Updated Content, Preview Content, Alias, Write Lock | 같은 구성; 엔티티 레지스트리 항목은 새로 생김 (unique ID 접두어가 `gicisky_`에서 `ble_esl_`로) |
| 옵션 | Retry Count, Write Delay, Prevent Duplicate Send, Debounce Delay | Retry Count, Prevent Duplicate Send, Debounce Delay — Write Delay는 없어짐(재시도가 알아서 간격을 둠); **Model** 옵션은 모델을 스스로 알리지 못하는 프로토콜에만 나타나고, PickSmart 태그는 광고에서 모델을 인식 |
| 모델 인식 | 광고에서 | 광고에서; 등록되지 않은 device number는 수동 모델 선택으로 |
| 폰트 | `custom_components/gicisky/fonts/`, 그다음 `config/www/fonts/` | `custom_components/ble_esl/fonts/`, 그다음 `config/www/fonts/` |
| 최소 Home Assistant | 2025.1 | **2025.12** |
| `ble_esl`에서 새로 생긴 것 | — | 다중 `target:` (기기 / 구역 / 층 / 레이블), `response_variable`로 태그별 결과, 진단 다운로드, 단계별 쓰기 타이밍 |

### 시작 전에

1. **Home Assistant 2025.12 이상**이 필요합니다.
2. 기존 기기에서 직접 바꿔 둔 것을 적어 둡니다 — 이어지지 않습니다:
   - **Alias** 텍스트 엔티티 값,
   - **옵션** (재시도 횟수, 중복 전송 방지, 디바운스),
   - 바꾼 엔티티 ID, 이름, 아이콘, 구역 지정.
3. 예전 액션을 부르는 곳을 모두 찾습니다. **개발자 도구 → 액션**이나 설정 파일 텍스트 검색으로 자동화, 스크립트, 블루프린트, Node-RED 플로우, 대시보드 버튼에서 `gicisky.write`와 `gicisky.write_guarded`를 찾으세요.
4. 아래 순서대로 진행합니다. 두 통합구성요소는 같은 Bluetooth 광고(제조사 ID `0x5053`)를 발견하므로, 둘 다 설치돼 있으면 서로 태그를 차지하려 들고 새 엔티티에 `_2` 접미사가 붙습니다.

### 1단계 — 기존 통합구성요소 항목 제거

**설정 → 기기 및 서비스 → 통합구성요소 → Gicisky**: 기기 항목을 하나씩 열어 삭제하거나(⋮ → **삭제**), 통합구성요소 전체를 삭제합니다.

### 2단계 — `hass-gicisky` 제거

- **HACS:** HACS → **통합구성요소** → *Gicisky* → ⋮ → **제거**. 그다음 사용자 지정 저장소(HACS → ⋮ → **사용자 지정 저장소**)에서도 지워서 보관된 저장소가 더 보이지 않게 합니다.
- **수동 설치:** `custom_components/gicisky` 폴더를 삭제합니다.

`config/www/fonts/`에 둔 사용자 폰트는 그대로 남고 계속 동작합니다. `custom_components/gicisky/fonts/` *안에* 복사해 넣은 폰트는 폴더와 함께 사라지니 먼저 `config/www/fonts/`로 옮기세요.

### 3단계 — `hass-ble-esl` 설치

1. HACS → **통합구성요소** → ⋮ → **사용자 지정 저장소** → `https://github.com/eigger/hass-ble-esl`, 분류 *Integration* → **BLE ESL** 설치. (또는 릴리스에서 `custom_components/ble_esl`을 수동 복사.)
2. **Home Assistant 재시작.**

### 4단계 — 태그 다시 추가

재시작 후 광고 중인 PickSmart 태그는 `hass-gicisky` 때와 똑같이 **설정 → 기기 및 서비스 → 발견됨**에 나타납니다. 하나씩 확인하세요. **통합구성요소 추가 → BLE ESL**로 수동 추가할 수도 있고, 범위 안의 미등록 태그가 모두 나열됩니다.

- 모델(크기, 색상, 패널 종류)은 태그의 광고에서 읽으므로 알려진 태그에는 모델 선택 단계가 없습니다.
- 태그의 device number가 아직 카탈로그에 없으면 목록에서 모델을 고르라고 합니다. 패널 크기와 색상이 맞는 항목을 고른 뒤, 진단 다운로드를 첨부해 [이슈를 열어](https://github.com/eigger/hass-ble-esl/issues) 주시면 device number를 추가할 수 있습니다.

기기 이름은 다시 `Gicisky <식별자>`가 되고, 식별자는 MAC 주소의 마지막 8자리(16진수)입니다. 이름 규칙이 같고 기존 엔티티를 먼저 지웠기 때문에 기본 엔티티 ID는 대개 똑같이 돌아옵니다(예: `image.gicisky_a1b2c3d4_last_updated_content`). 기기 페이지에서 확인하고, 엔티티 ID를 바꿔 썼다면 다시 바꾸세요.

### 5단계 — 옵션 다시 설정

**설정 → 기기 및 서비스 → BLE ESL → 기기 → 구성**에서 Retry Count, Prevent Duplicate Send, Debounce Delay를 적어 둔 값으로 맞춥니다. 쓰고 있었다면 **Alias** 텍스트 엔티티와 **Write Lock** 스위치도 설정합니다.

### 6단계 — 자동화, 스크립트, 대시보드 수정

액션 이름만 바꾸고 나머지는 그대로 둡니다.

```diff
-action: gicisky.write
+action: ble_esl.write
 target:
   device_id: 1234567890abcdef1234567890abcdef
 data:
   payload:
     - type: text
       value: Hello World!
       x: 10
       y: 10
       size: 40
```

```diff
-action: gicisky.write_guarded
+action: ble_esl.write_guarded
 target:
   device_id: 1234567890abcdef1234567890abcdef
 data:
   debounce_override_ms: 0
   payload: ...
```

같이 고칠 것:

- **`device_id` 대상** — 기기가 새로 만들어져 ID가 바뀝니다. 자동화 편집기에서 기기를 다시 고르거나, 태그가 있는 구역/레이블을 대상으로 바꾸세요(`ble_esl`은 `area_id`, `floor_id`, `label_id`, 엔티티 대상을 받고, 한 번에 여러 태그도 됩니다).
- 대시보드, 템플릿, 조건의 **엔티티 참조** (`sensor.gicisky_…_battery`, `binary_sensor.gicisky_…_display_in_sync`, `image.gicisky_…_last_updated_content` 등) — 보통 그대로지만 확인하세요.
- 도메인 `gicisky.`를 하드코딩한 **블루프린트 / 패키지**.

`payload:` 아래의 모든 것(요소, 폰트, `dlimg` URL, `plot` 엔티티, `dither`)은 수정 없이 동작합니다. Gicisky 태그용으로 만들어진 [예제](../../examples/README.md)와 웹 도구도 이 저장소가 제공하는 것과 같습니다.

### 7단계 — 확인

1. **개발자 도구 → 액션**에서 `ble_esl.write`를 `dry_run: true`로 호출하고 **Preview Content** 이미지 엔티티가 예전처럼 렌더링되는지 봅니다.
2. 실제로 한 번 써서 **Display In Sync**가 켜지고 **Failure Count**가 0으로 유지되는지 확인합니다.
3. 쓰기가 실패하면 **Write Duration** 센서 속성(`attempt`, `error`, `start_probes`, `round_trip_ms`)을 보거나 기기 페이지에서 **⋮ → 진단 다운로드**를 받으세요 — 백엔드, 프리셋, 펌웨어, 옵션, 마지막 광고가 들어 있고, 이슈 리포트에 필요한 것이 그것입니다. 자세한 읽는 법은 [트러블슈팅](troubleshooting.md)에 있습니다.

### 자주 묻는 것

**꼭 옮겨야 하나요?** `hass-gicisky`는 Home Assistant가 깨뜨리지 않는 한 계속 동작하지만, 보관 처리되어 수정이 들어가지 않습니다. 새 태그 모델, 프로토콜 수정, 기능은 `hass-ble-esl`에만 들어갑니다.

**둘을 동시에 쓸 수 있나요?** 쓸모 있게는 안 됩니다: 두 통합구성요소가 같은 광고를 발견하고 태그를 두고 경쟁합니다. 예전 것을 먼저 지우세요.

**이미지 전송 방식이 달라졌나요?** 아니요. PickSmart writer, 압축, 프리셋은 `hass-gicisky`에서 그대로 가져왔고, 실기기에서 검증된 유일한 백엔드입니다. [models.md](../models.md)의 모델 표를 보세요.

**히스토리는요?** Recorder 히스토리는 엔티티 ID 기준입니다. 새 엔티티가 예전과 같은 ID를 받으면 장기 통계가 이어지고, 아니면 예전 히스토리는 삭제될 때까지 예전 ID 아래 남습니다.

### `hass-zhsunyco`에서 오는 경우

`hass-zhsunyco`는 이 저장소로 이름이 바뀐 것이라 `zhsunyco` 도메인도 같은 도메인 변경을 거쳤습니다. 위 단계가 그대로 적용되고, 다른 점은 다음과 같습니다:

- **Zhsunyco** 항목과 `custom_components/zhsunyco`를 제거합니다; 액션은 `zhsunyco.write` / `zhsunyco.write_guarded` 대신 `ble_esl.write` / `ble_esl.write_guarded`가 됩니다.
- easyTag 태그는 모델을 스스로 알리지 못하므로 설정 흐름과 **옵션** 대화상자에 **Model** 선택이 있습니다 — 쓰던 것과 같은 크기를 고르세요. 디스플레이 버전을 아는 WOLINK 태그는 그 단계를 건너뛰고, 그 외 WOLINK 태그는 설정할 때 한 번만 고르며 **옵션**에서는 다시 고르지 않습니다.
- 기기 이름은 `Zhsunyco <id>` 그대로라, Gicisky 태그처럼 기본 엔티티 ID가 대개 똑같이 돌아옵니다.
