<!-- hass-standards:header:start -->
# BLE ESL

Home Assistant를 위한 Bluetooth Low Energy 전자식 매대 표시기(ESL) 통합입니다.

[English](README.md) | **한국어**

<!-- hass-standards:badges:start -->
[![Release](https://img.shields.io/github/v/release/eigger/hass-ble-esl?style=flat)](https://github.com/eigger/hass-ble-esl/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat)](#설치)
[![Home Assistant minimum](https://img.shields.io/badge/HA-%E2%89%A5%202025.12.0-41BDF5?style=flat)](hacs.json)
[![Tests](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/tests.yml?branch=main&style=flat&label=Tests)](https://github.com/eigger/hass-ble-esl/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/validate.yml?branch=main&style=flat&label=Validate)](https://github.com/eigger/hass-ble-esl/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl?style=flat)](LICENSE)
[![Analytics reporting installs](https://img.shields.io/badge/dynamic/json?style=flat&color=41BDF5&label=Usage&query=%24.ble_esl.total&url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json)](https://analytics.home-assistant.io/)
<!-- hass-standards:badges:end -->
<!-- hass-standards:header:end -->

**배터리 하나로 수개월에서 수년 동안 Home Assistant 데이터를 보여주는 e-paper 디스플레이.** BLE ESL은 [HACS](https://hacs.xyz/) 사용자 지정(custom) 통합구성요소입니다: 액션 한 번으로 캘린더, 날씨, 센서 값, 사진을 블루투스로 태그에 보냅니다 — 게이트웨이도, 클라우드도, 배선도 없습니다. Home Assistant Core에 포함된 통합이 아니며 Core 품질 등급을 주장하지 않습니다. [왜 e-paper 태그인가? →](docs/ko/usage.md#왜-e-paper-태그인가)

| 2.1" (250×128) | 2.9" (296×128) | 4.2" (400×300) | 10.2" (960×640) |
|---|---|---|---|
| <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/21_1.png" alt="2.1 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/29_1.png" alt="2.9 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png" alt="4.2 inch Poshiji PSJ-420" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/102_1.jpg" alt="10.2 inch Gicisky" width="200" /> |
| Gicisky | Gicisky | Poshiji PSJ-420 | Gicisky |

실제 태그 사진입니다. [YAML이 포함된 예제 더 보기 →](examples/README.md) (영어)

## 지원 태그

BLE 프로토콜 계열과 판매 브랜드는 다음과 같습니다:

| 프로토콜 | 브랜드 | 크기 | 색상 | 상태 | 구매 |
|---|---|---|---|---|---|
| **ETAG** | Hipoink | 2.13" (250 × 122) | BWR | ✅ 검증; [프로토콜 노트](docs/etag.md) (영어) | [AliExpress](https://de.aliexpress.com/item/1005009110927073.html) |
| **PickSmart** | Gicisky | 2.1" – 10.2" | BW / BWR / BWRY | ✅ 실기기 검증 | [AliExpress](https://ko.aliexpress.com/item/1005002399342939.html) |
| **XTE** | Poshiji | 1.54" – 7.5" | BWRY | ✅ 2.13", 2.66", 2.9", 4.2"는 실기기 검증 완료; 다른 크기는 크기만 맞춘 프리셋 | [AliExpress](https://ko.aliexpress.com/item/1005012725381116.html) |
| **WOLINK** | Zhsunyco | 1.54" – 13.3" | BWR / BWRY | ✅ 1.54", 2.66", 3.5", 3.7", 4.2" BWRY와 2.9" BWR 실기기 검증 완료; 다른 크기는 미검증 | [AliExpress](https://ko.aliexpress.com/item/1005009231276243.html) |
| **easyTag** | Zhsunyco | 1.54" – 10.2" | BW / BWR | ⚠️ 사양서 기반, 미검증 | — |

해상도와 모델 코드가 있는 전체 목록: **[docs/models.md](docs/models.md)** (영어). 다른 프로토콜을 쓰는 태그가 있나요? [프로토콜 추가하기](custom_components/ble_esl/esl_ble/README.md) (영어)를 보세요.

주요 기능:

- 두 액션 `ble_esl.write`와 `ble_esl.write_guarded`(바뀌지 않은 이미지는 건너뛰고, Write Lock 스위치를 존중하며, 연속 호출을 디바운스). 레이아웃은 [imagespec](https://github.com/eigger/imagespec) 요소와 Jinja 템플릿으로 적습니다.
- **ESL Manager**: 같은 payload를 YAML로 내보내는 사이드바 대시보드와 비주얼 디자이너.
- 쓰기가 어느 단계에서, 어떤 라디오를 거쳐 실패했는지 알려 주는 실패 센서와 진단 다운로드.

## 요구사항

- Home Assistant **2025.12** 이상. 권장 설치에는 [HACS](https://hacs.xyz/)가 필요합니다.
- **active 연결**을 지원하는 Bluetooth 어댑터나 ESPHome Bluetooth 프록시([Bluetooth](#bluetooth) 참고).
- 위 표의 지원 태그.

## 설치

1. **HACS**(사용자 지정 저장소 `eigger/hass-ble-esl`)로 설치하거나, `custom_components/ble_esl`을 설정 폴더에 복사합니다.
2. Home Assistant를 재시작합니다.
3. 범위 안의 태그는 자동으로 발견됩니다 — **설정 → 기기 및 서비스**에서 확인하거나, **통합구성요소 추가 → BLE ESL**로 추가합니다.

옵션(Retry Count, Prevent Duplicate Send, Debounce Delay, WOLINK / easyTag의 Model)은 **구성**에 있습니다. [docs/ko/usage.md](docs/ko/usage.md#옵션)를 보세요.

`hass-gicisky`나 `hass-zhsunyco`에서 오셨나요? 태그를 새 `ble_esl` 도메인으로 다시 추가하고 `gicisky.write`를 `ble_esl.write`로 바꿔야 합니다 — 페이로드는 그대로입니다. **[마이그레이션 가이드 →](docs/ko/migration.md)**

### Bluetooth

가능하면 호스트 내장 어댑터 대신 **Bluetooth 프록시**를 쓰고, **active**로 설정하세요(`bluetooth_proxy: active: true`, 시작 설정으로 `esp32_ble_tracker: scan_parameters: active: true`도 함께) — 쓰기 문제 대부분은 패시브 프록시나 약한 어댑터에서 옵니다. 스캔 간격은 기본값으로 둡니다. 발견된 태그가 곧 연결이 되는 것은 아닙니다: 첫 GATT 연결은 첫 쓰기 때 일어납니다. BLE ESL은 태그와 페어링하지 않습니다. 제조사 앱을 닫고(ETAG), 같은 태그에 쓰는 다른 통합이 없게 하세요.

ESPHome 설정 예, 하드웨어 추천, BLE ESL 고유 사항: [docs/ko/bluetooth.md](docs/ko/bluetooth.md). 공통 프록시 설정·추천 하드웨어·연결 문제 확인 순서: [Bluetooth proxy 가이드](https://github.com/eigger/hass-repo-standards/blob/main/docs/bluetooth.ko.md). 태그별 조건과 실패 센서는 [docs/ko/troubleshooting.md](docs/ko/troubleshooting.md)를 참고하세요.

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

몇 초 뒤 태그가 갱신됩니다. `dry_run: true`를 붙이면 보내지 않고 렌더링만 하며, 결과는 태그의 **Preview Content** 이미지 엔티티에 나타납니다. 더 보기: [사용 개요](docs/ko/usage.md), [`examples/`](examples/README.md)(영어)의 완성된 레이아웃, 비주얼 [디자이너 가이드](docs/ko/designer.md).

## 제한사항과 주의

> [!WARNING]
> 미검증 WOLINK 및 easyTag 프리셋은 기술 사양서로 만들어졌으며 실제 태그에서 테스트되지 않았습니다. 써 보셨다면 [Discussions](https://github.com/eigger/hass-ble-esl/discussions)에 결과를 알려 주세요.

- XTE의 2.13", 2.66", 2.9", 4.2" 외 크기는 손으로 고르는 크기만 맞춘 프리셋입니다. 하드웨어와 맞지 않는 프리셋은 쓰기는 성공해도 화면이 이상하게 나올 수 있습니다.
- **Preview Content**는 렌더링한 결과이며 패널에서 읽어 온 것이 아닙니다.
- 디자이너는 센서 변경 시 자동 전송하지 않습니다. 자동화로 갱신 시점을 정하세요. e-paper는 LCD가 아니므로 너무 잦은 갱신은 피하세요. `write_guarded`와 Prevent Duplicate Send / Debounce Delay 옵션이 도움이 됩니다.

## 문서

| 주제 | 한국어 | English |
|---|---|---|
| 사용 개요: 첫 레이아웃, 비주얼 에디터, 액션, 옵션, 페이로드와 렌더링 | [docs/ko/usage.md](docs/ko/usage.md) | [docs/usage.md](docs/usage.md) |
| Bluetooth 설정 | [docs/ko/bluetooth.md](docs/ko/bluetooth.md) ([Bluetooth proxy 안내](https://github.com/eigger/blesession/blob/main/docs/bluetooth.ko.md)) | [docs/bluetooth.md](docs/bluetooth.md) |
| 트러블슈팅과 제보 | [docs/troubleshooting.ko.md](docs/troubleshooting.ko.md) | [docs/troubleshooting.md](docs/troubleshooting.md) |
| 액션, 응답 데이터, 엔티티, 폰트 | — (영어만) | [docs/actions.md](docs/actions.md) |
| 지원 모델과 구매처 | — (영어만) | [docs/models.md](docs/models.md) |
| ESL Manager / 디자이너 | [docs/ko/designer.md](docs/ko/designer.md) | [docs/designer.md](docs/designer.md) |
| 디자인 템플릿 | [docs/ko/design-templates.md](docs/ko/design-templates.md) | [docs/design-templates.md](docs/design-templates.md) |
| Migration from hass-gicisky / hass-zhsunyco | [docs/ko/migration.md](docs/ko/migration.md) | [docs/migration.md](docs/migration.md) |
| 프로토콜 노트 (ETAG, XTE) | — (영어만) | [docs/etag.md](docs/etag.md), [docs/xte.md](docs/xte.md) |
| 예제 | — (영어만) | [examples/README.md](examples/README.md) |
| 개발: 테스트, 검증 환경, 린트, 프로토콜 추가 | — (영어만) | [docs/development.md](docs/development.md) |

<!-- hass-standards:support:start -->
## 지원

- [Issues](https://github.com/eigger/hass-ble-esl/issues): 버그를 신고하거나 기능을 요청하세요.
<!-- hass-standards:support:end -->

<!-- hass-standards:related-projects:start -->
## 관련 프로젝트

- [imagespec](https://github.com/eigger/imagespec): ESL 태그 payload 뒤의 선언적 레이아웃 및 렌더러.
- [Stash](https://github.com/eigger/stash): ESL 태그에 직접 라벨을 출력하는 가정 재고 관리 시스템.
- [hass-gicisky](https://github.com/eigger/hass-gicisky): 보관 처리된 전신 통합구성요소.
<!-- hass-standards:related-projects:end -->

<!-- hass-standards:license:start -->
## 라이선스

[MIT License](LICENSE) 라이선스로 배포됩니다.
<!-- hass-standards:license:end -->
