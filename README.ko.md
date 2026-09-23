# hass-ble-esl
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=home-assistant)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/eigger/hass-ble-esl.svg)](https://github.com/eigger/hass-ble-esl/releases)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl)](https://github.com/eigger/hass-ble-esl/blob/main/LICENSE)
![integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=%24.ble_esl.total)

**[English](README.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 README](README.md)를 따릅니다.

범용 BLE 전자가격표시기(ESL) Home Assistant 통합구성요소

**배터리 하나로 수개월에서 수년 동안 Home Assistant 데이터를 보여주는 e-paper 디스플레이.** 액션 한 번으로 캘린더, 날씨, 센서 값, 사진을 블루투스로 태그에 보냅니다 — 게이트웨이도, 클라우드도, 배선도 없습니다.

| 2.1" (250×128) | 2.9" (296×128) | 4.2" (400×300) | 10.2" (960×640) |
|---|---|---|---|
| <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/21_1.png" alt="2.1 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/29_1.png" alt="2.9 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png" alt="4.2 inch Poshiji PSJ-420" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/102_1.jpg" alt="10.2 inch Gicisky" width="200" /> |
| Gicisky | Gicisky | Poshiji PSJ-420 | Gicisky |

실제 태그 사진입니다. [YAML이 포함된 예제 더 보기 →](examples/README.md)

## 왜 e-paper 태그인가?

**전자가격표시기(ESL)** 는 마트 선반에서 가격을 보여주는 그 디스플레이입니다: 자체 배터리와 블루투스 라디오가 달린 **e-paper**(e-ink) 화면이죠. e-paper는 그림이 *바뀔 때*만 전력을 쓰고, 정지 화면을 유지하는 데는 전력이 들지 않습니다. 그래서 배터리 하나로 수개월에서 수년을 버티고, 햇빛 아래에서도 인쇄물처럼 읽히며, 빛을 내지 않습니다.

콘센트가 없는 자리에 *그냥 붙어 있어야 하는* 정보에 딱 맞습니다: 문 앞의 회의실 캘린더, 현관의 오늘 날씨, 냉장고의 분리수거 요일, "누가 집에 있나" 보드, 3D 프린터 진행률, 수납함의 재고 라벨. 아무 데나 붙여 두고 충전은 잊으면 됩니다.

이 통합구성요소는 Home Assistant에서 BLE로 태그에 직접 이야기합니다. 레이아웃을 YAML로 적으면(텍스트, 아이콘, QR 코드, 차트, 이미지 — 엔티티에서 나오는 무엇이든) 태그가 그걸 보여줍니다.

## 지원 태그

BLE 프로토콜 4계열, 판매 브랜드는 다음과 같습니다:

| 프로토콜 | 브랜드 | 크기 | 색상 | 상태 | 구매 |
|---|---|---|---|---|---|
| **PickSmart** | Gicisky | 2.1" – 10.2" | BW / BWR / BWRY | ✅ 실기기 검증 | [AliExpress](https://ko.aliexpress.com/item/1005002399342939.html) |
| **XTE** | Poshiji | 1.54" – 7.5" | BWRY | ✅ PSJ-420은 소유자 검증; 다른 크기는 크기만 맞춘 프리셋 | [AliExpress](https://ko.aliexpress.com/item/1005012725381116.html) |
| **WOLINK** | Zhsunyco | 1.54" – 13.3" | BWR / BWRY | ⚠️ 사양서 기반, 미검증 | [AliExpress](https://ko.aliexpress.com/item/1005009231276243.html) |
| **easyTag** (eLabel) | Zhsunyco | 1.54" – 10.2" | BW / BWR | ⚠️ 사양서 기반, 미검증 | — |

해상도와 모델 코드가 있는 전체 목록: **[docs/models.md](docs/models.md)**. 다른 프로토콜을 쓰는 태그가 있나요? [프로토콜 백엔드 추가하기](custom_components/ble_esl/esl_ble/README.md)를 보세요.

> [!WARNING]
> WOLINK와 easyTag 프리셋은 기술 사양서로 만들었고 실제 태그에서 테스트되지 않았습니다. 써 보셨다면 [Discussions](https://github.com/eigger/hass-ble-esl/discussions)에 결과를 알려 주세요.

## 설치

Home Assistant **2025.12** 이상이 필요합니다.

1. **HACS**(사용자 지정 저장소 `eigger/hass-ble-esl`)로 설치하거나, `custom_components/ble_esl`을 설정 폴더에 복사합니다.
2. Home Assistant를 재시작합니다.
3. 범위 안의 태그는 자동으로 발견됩니다 — **설정 → 기기 및 서비스**에서 확인하거나, **통합구성요소 추가 → BLE ESL**로 추가합니다.

가능하면 호스트 내장 어댑터 대신 **Bluetooth 프록시**를 쓰고, **active**로 설정하세요 — 쓰기 문제 대부분은 패시브 프록시나 약한 어댑터에서 옵니다. 스캔 간격은 기본값으로 둡니다.

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

> [!TIP]
> 하드웨어 추천: [Seeed Studio XIAO W5500](https://ko.aliexpress.com/item/1005009310322353.html)(유선 이더넷이 달린 XIAO ESP32)이 좋은 프록시입니다 — 이더넷을 쓰면 라디오가 BLE에만 쓰입니다. 다른 보드는 커뮤니티 글 [Great ESP32 board for an ESPHome Bluetooth proxy](https://community.home-assistant.io/t/great-esp32-board-for-an-esphome-bluetooth-proxy/916767/31)를 참고하세요.

`hass-gicisky`나 `hass-zhsunyco`에서 오셨나요? 태그를 새 `ble_esl` 도메인으로 다시 추가하고 `gicisky.write`를 `ble_esl.write`로 바꿔야 합니다 — 페이로드는 그대로입니다. **[마이그레이션 가이드 →](docs/ko/migration.md)**

## 빠른 시작

**개발자 도구 → 액션**에서:

```yaml
action: ble_esl.write
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Hello World!
      x: 10
      y: 10
      size: 40
```

몇 초 뒤 태그가 갱신됩니다. `dry_run: true`를 붙이면 보내지 않고 렌더링만 합니다 — 결과는 태그의 **Preview Content** 이미지 엔티티에 나타나므로, 패널을 소모하지 않고 레이아웃을 다듬을 수 있습니다.

레이아웃은 [imagespec](https://github.com/eigger/imagespec) 요소의 목록입니다 — 텍스트, 아이콘, 선, QR 코드, 진행 바, 게이지, 파이/막대 차트, 히스토리 플롯, 다운로드 이미지 — 그리고 어떤 값이든 엔티티를 참조하는 Jinja 템플릿이 될 수 있습니다. 지원 해상도별로 완성된 레이아웃은 [`examples/`](examples/README.md)에 있고, [Payload Editor](https://eigger.github.io/Gicisky_Payload_Editor.html)와 [Image Uploader](https://eigger.github.io/Gicisky_Image_Uploader.html) 웹 도구로 브라우저에서 초안을 만들 수 있습니다.

## 액션

두 액션 모두 표준 `target:`(태그 기기, 그 엔티티, 또는 태그가 속한 구역/층/레이블)을 받고 대상마다 차례로 씁니다.

| 액션 | 용도 |
|---|---|
| `ble_esl.write` | 항상 전송 (`dry_run` 제외) |
| `ble_esl.write_guarded` | 자주 발화하는 자동화용: 바뀌지 않은 이미지는 건너뛰고, **Write Lock** 스위치를 존중하며, 연속 호출을 디바운스 |

| 파라미터 | 기본값 | 설명 |
|---|---|---|
| `payload` | — | [imagespec 요소](https://github.com/eigger/imagespec/blob/main/docs/elements.md) 목록 (필수) |
| `rotate` | `0` | `0`, `90`, `180`, `270` |
| `background` | `white` | `white`, `black`, `red`, `yellow` |
| `dry_run` | `false` | **Preview Content**에 렌더링만 |
| `debounce_override_ms` | 옵션 값 | `write_guarded` 전용: 이 호출의 디바운스를 덮어씀 (`0` = 즉시) |

두 액션 모두 `response_variable`로 태그별 결과를 돌려줄 수 있습니다. 전체 레퍼런스 — 사진·차트 디더링, 회전, 응답 데이터, 태그별 엔티티, 폰트: **[docs/actions.md](docs/actions.md)** (영어).

## 옵션

**설정 → 기기 및 서비스 → BLE ESL → 구성**:

| 옵션 | 기본값 | 범위 | 설명 |
|--------|---------|-------|-------------|
| **Model** | — | 모델 목록 | 모델을 스스로 알리지 못하는 프로토콜(WOLINK, easyTag)에만 표시 |
| **Retry Count** | 3 | 1–10 | BLE 쓰기 실패 시 재시도 횟수 |
| **Prevent Duplicate Send** | 꺼짐 | 켬/끔 | 이미지가 바뀌지 않았으면 전송 생략 |
| **Debounce Delay (ms)** | 0 | 0–120000 | 쓰기 전 대기; 새 요청이 오면 대기 중인 요청은 취소 |

> [!TIP]
> 자주 발화하는 자동화라면 **Prevent Duplicate Send**나 **Debounce Delay**를 켜서 태그 배터리와 BLE 점유를 아끼세요. 전송 중에 실패한 쓰기는 다음 재시도에서 패킷 간격을 더 두고 보냅니다; 계속 실패하면 **Write Duration** 센서의 속성이 링크 문제인지 배치 문제인지 알려줍니다 — [docs/ko/troubleshooting.md](docs/ko/troubleshooting.md)를 보세요.

## 페이로드와 렌더링

레이아웃은 **[imagespec](https://github.com/eigger/imagespec)** 이 렌더링합니다; 요소와 필드의 기준 문서는 그쪽입니다:

| 주제 | 링크 |
|-------|------|
| 미리보기 이미지가 있는 요소 예제 | [imagespec/docs/elements.md](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| 모든 요소 필드와 기본값 | [imagespec README — Element Reference](https://github.com/eigger/imagespec#elements-reference) |
| 레이아웃, 팔레트, LLM 작성 가이드 | [imagespec/docs/authoring.md](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) |
| 디더링 (요소 단위만) | [imagespec/docs/dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md) |

이 통합구성요소가 그 위에 더하는 것:

- **해상도와 팔레트**는 호출이 아니라 태그의 프리셋에서 옵니다. 팔레트 밖의 색은 가장 가까운 지원 색(BW, BWR, BWRY)으로 양자화됩니다.
- **회전** (`rotate: 90/180/270`)은 캔버스를 돌립니다; 출력 크기는 패널 크기 그대로입니다.
- **디더링**은 요소 단위입니다: 사진과 차트(`dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge`)에 `dither`를 붙이고, 텍스트에는 붙이지 마세요.
- **`plot`** 은 Recorder에서 히스토리를 읽습니다; **`dlimg`** 는 `/config/...` 경로, HTTP(S) URL, data URI를 받습니다.
- **폰트:** 기본은 `NotoSansKR-Regular.ttf`; `config/www/fonts/`에 `.ttf`를 넣고 이름으로 참조합니다. [fonts](docs/actions.md#fonts)를 보세요.
- 좌표를 손으로 찍기보다 `row` / `column` / `stack` 레이아웃을 쓰세요.

## 피드백과 지원

- 라벨이 갱신되지 않나요? **[docs/ko/troubleshooting.md](docs/ko/troubleshooting.md)** — 실패 센서가 쓰기가 어디서, 왜 죽었는지 알려줍니다.
- 버그를 찾으셨나요? [이슈를 열고](https://github.com/eigger/hass-ble-esl/issues) 태그의 진단 파일을 첨부해 주세요: **기기 페이지 → ⋮ → 진단 다운로드**. 백엔드, 프리셋, 펌웨어, 옵션, 마지막 광고, 실패 카운터가 들어 있습니다(MAC은 가려짐).
- 질문이나 아이디어? [Discussions](https://github.com/eigger/hass-ble-esl/discussions)
- WOLINK나 easyTag 태그를 테스트하셨거나, 수동 모델 선택을 요구한 Poshiji 크기가 있나요? 알려 주세요 — 그렇게 프리셋이 검증됩니다.

## 관련 프로젝트

- [imagespec](https://github.com/eigger/imagespec) — `payload:` 뒤에서 도는 렌더링 엔진
- [Stash](https://github.com/eigger/stash) — Home Assistant를 통해 ESL 태그에 라벨을 출력하는 셀프호스팅 가정 재고 관리자
- [hass-gicisky](https://github.com/eigger/hass-gicisky) — 보관 처리된 PickSmart 전용 전신 ([마이그레이션 가이드](docs/ko/migration.md))
- [Development](docs/development.md) — 테스트, 린트, 프로토콜 추가 (영어)
