# Bluetooth 설정

**[English](../bluetooth.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 원문](../bluetooth.md)을 따릅니다.

BLE ESL은 이미지를 보낼 때 태그마다 GATT로(`blesession`을 통해) 연결합니다. Home Assistant에는 **active 연결**이 가능한 Bluetooth 어댑터나 ESPHome Bluetooth 프록시가 필요합니다. 태그의 광고가 보인다고 해서 쓸 수 있는 것은 아닙니다.

공통 프록시 설정·추천 하드웨어·일반적인 연결 문제 확인 순서는 [Bluetooth proxy 가이드](https://github.com/eigger/blesession/blob/main/docs/bluetooth.ko.md)에 있습니다. 이 문서에는 BLE ESL 고유 내용만 남기고, 태그별 조건과 실패 센서는 [troubleshooting.md](troubleshooting.md)에 있습니다.

## 프록시 설정

원격 Bluetooth 연결에는 **active 연결**이 가능한 **Bluetooth 프록시**를 쓰세요. 안정적인 로컬 어댑터도 사용할 수 있으며 패시브 스캔 자체가 GATT 연결을 막지는 않습니다. 스캔 간격은 기본값으로 둡니다.

아래는 ESP32 ESPHome 설정 중 Bluetooth 부분만 보인 것이며 전체 펌웨어 파일이 아닙니다. 보드·네트워크·API 설정이 있는 기존 설정과 합쳐 사용하세요.

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

두 `active`는 역할이 다릅니다.

- `bluetooth_proxy.active: true`는 Home Assistant가 프록시를 통해 **GATT 연결**을 열 수 있게 합니다. BLE ESL은 모든 쓰기에 이것이 필요하며, 이 설정이 없는 프록시는 광고만 전달합니다.
- `esp32_ble_tracker.scan_parameters.active: true`는 scan response를 요청하는 **스캔 방식**입니다. BLE ESL에서 쓰는 시작 설정이지만, 이것 자체가 연결을 가능하게 하는 설정은 아닙니다.

> [!TIP]
> 하드웨어 추천: [Seeed Studio XIAO W5500](https://ko.aliexpress.com/item/1005009310322353.html)(유선 이더넷이 달린 XIAO ESP32)이 좋은 프록시입니다 — 이더넷을 쓰면 라디오가 BLE에만 쓰입니다. 다른 보드는 커뮤니티 글 [Great ESP32 board for an ESPHome Bluetooth proxy](https://community.home-assistant.io/t/great-esp32-board-for-an-esphome-bluetooth-proxy/916767/31)를 참고하세요. 구매할 보드 리비전(XIAO W5500 **V1.2**)과 USB-A 동글형 대안은 공통 가이드에 있습니다.

이 추천이 모든 프록시·태그 조합을 BLE ESL로 시험했다는 뜻은 아닙니다. 이미 안정적으로 동작하는 로컬 어댑터가 있다면 교체할 필요는 없습니다.

## BLE ESL 고유 사항

- **발견은 연결이 아닙니다.** Home Assistant에 나타난(광고로 발견된) 태그는 아직 연결된 적이 없습니다. 실제 GATT 연결은 첫 쓰기 때 일어납니다. [발견과 연결의 차이](troubleshooting.md#발견과-연결의-차이)를 보세요.
- **쓰기는 한 번에 하나.** 모든 태그의 쓰기가 BLE 잠금 하나를 공유합니다. 한 번에 한 시도만 라디오를 잡고, 재시도해야 하는 태그는 다른 태그에 먼저 순서를 넘깁니다.
- **통합구성요소 옵션은 프록시 설정이 아닙니다.** Retry Count, Prevent Duplicate Send, Debounce Delay는 BLE ESL 옵션입니다([usage.md](usage.md#옵션)). 프록시 펌웨어를 바꾸지 않으며 다른 Bluetooth 통합의 기본값도 아닙니다.
- **프로토콜별 조건**(인증, 최소 쓰기 크기, 제조사 앱)은 [troubleshooting.md](troubleshooting.md#프로토콜별-조건)에 있습니다.
