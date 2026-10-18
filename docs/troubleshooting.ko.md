# 문제 해결

[README](../README.ko.md) | [English](troubleshooting.md) | **한국어**

## 공통 문제 해결

먼저 [공통 Bluetooth 문제 해결](https://github.com/eigger/blesession/blob/main/docs/troubleshooting.ko.md)을 확인하세요. 프록시 선택·펌웨어·Home Assistant 등록은 [Bluetooth proxy 안내](https://github.com/eigger/blesession/blob/main/docs/bluetooth.ko.md)를 따르세요. BLE ESL 전용 프록시 설정은 [bluetooth.md](bluetooth.md)를 참고하세요.

## 기기별 확인 사항

### 발견과 연결의 차이

Home Assistant에 태그가 나타났다는 것은 **발견**되었다는 뜻일 뿐입니다: 어떤 라디오가 광고를 받았다는 것입니다. GATT 연결, 프로토콜 핸드셰이크, 이미지 전송이 될지는 아직 알 수 없고, 이것들은 쓰기가 실행될 때만 일어납니다. **Signal Strength** 센서와 진단의 광고 정보는 발견에서 오고, 쓰기 센서(`failed_stage`, `via`, 단계별 타이밍)는 연결에서 옵니다.

- 태그를 가장 잘 들은 라디오가 실제 연결에 쓰인 라디오라는 보장은 없습니다. `via`는 링크가 사용한 라디오이며, `via_unconfirmed`가 `true`이면 태그를 가장 잘 들은 라디오일 뿐입니다. 가장 강한 광고를 받은 라디오가 링크와 다르면 `advertised_via`가 나타납니다.
- 연결하려면 ESPHome 프록시에 `bluetooth_proxy.active: true`가 필요합니다(또는 연결 가능한 로컬 어댑터). 이 설정이 없는 프록시는 광고만 전달합니다. [bluetooth.md](bluetooth.md#프록시-설정)를 확인하세요.
- BLE ESL은 어떤 태그와도 페어링·본딩하지 않으며, 이 통합구성요소의 어떤 프로토콜에도 깨우기 단계(버튼 누르기 등)가 없습니다. 쓰기 시도마다 연결을 최대 두 번 시도하는데, 잠든 태그가 두 번째 시도에 응답하는 경우가 많기 때문입니다. 특정 태그 모델을 손으로 깨워야 하는지는 **검증되지 않았습니다**.

### 프로토콜별 조건

링크가 올라온 뒤 각 프로토콜이 하는 일을 [`esl_ble/`](../custom_components/ble_esl/esl_ble/README.md) 구현 기준으로 정리했습니다. *검증되지 않음*으로 적힌 칸은 어느 쪽으로도 주장하지 않습니다.

| 프로토콜 | 인증 / 페어링 | 다른 앱·통합 | 전송 제약 |
|---|---|---|---|
| **PickSmart** (Gicisky) | 페어링·인증 없음. 알림 구독 후 0.2초 기다렸다가 START를 최대 3번(각 0.4초) 보냅니다. 응답이 없으면 `start_probes: 3`인 `auth` 실패입니다. | 검증되지 않음. 제조사 앱이나 다른 통합이 태그에 연결되어 있다면 쓰기 전에 끊으세요. | 240바이트 단위로 보내고 태그가 각각 응답합니다. 태그가 같은 조각을 다시 요청할 수 있으며, 한 조각을 연속 6번 요청하면 쓰기를 포기합니다. |
| **WOLINK** (Zhsunyco) | BLE 페어링 없음. 태그가 인증 특성으로 nonce를 주고 통합구성요소가 답합니다. 답이 틀리면 태그가 링크를 끊고 *device error 5: unlock failed*로 보고됩니다. | 검증되지 않음. 쓰기 전에 다른 앱이나 게이트웨이 연결을 끊으세요. | 조각 크기는 협상된 MTU를 따릅니다(200–506바이트, 200 미만으로는 내려가지 않음). 완료 대기는 패널 리프레시이며 이미지 크기에 따라 늘어납니다. WOLINK는 모델을 알리지 않으므로 **Model** 옵션을 손으로 골라야 합니다. |
| **easyTag** (Zhsunyco) | 페어링·인증 교환 없음. 실제 태그에서 시험하지 않았습니다. | 검증되지 않음. | 고정 패킷 간격(20ms)과 프레임당 20초 응답 대기. 완료 대기는 패널 리프레시입니다. **Model** 옵션을 손으로 골라야 합니다. |
| **ETAG** (Hipoink) | 페어링 없음. 연결 후 패널 펌웨어를 읽고, 모르는 펌웨어는 재시도 없이 거부합니다(`SE0213NP61-TNG-A0` 검증, `SE0213MN50-TNG-A0` 미검증). | Home Assistant에서 연결하기 전에 **제조사 Bluetooth Label 앱을 닫으세요**([etag.md](etag.md)). | 240바이트 패킷 하나가 write-without-response 한 번에 들어가야 하므로 ATT MTU가 243 이상이어야 합니다. 그보다 작으면 `ETAG write size … is too small`로 실패합니다. 패킷마다 응답을 받고, 명령 응답은 최대 30초 기다립니다. |
| **XTE** (Poshiji) | 페어링·인증 없음. 픽셀 배치가 구현되지 않은 프리셋(일부 device number)은 **연결 전에** 거부합니다. | **태그에 쓰는 통합은 하나만** 있어야 합니다([xte.md](xte.md)). | 알림 구독 후 0.5초 대기. 244바이트와 링크가 보고한 쓰기 한도 중 작은 값으로 씁니다(20바이트도 허용). 크기만 맞춘 프리셋은 손으로 고르며 미검증입니다. |

거부된 쓰기(지원하지 않는 펌웨어, 프리셋, device number)는 재시도하지 않습니다. 다시 시도해도 답이 바뀌지 않기 때문입니다.

**전원:** 배터리가 약하면 태그가 광고는 하지만 부하가 걸릴 때 링크가 끊기거나(`link_lost`) 패널 리프레시에 실패할 수 있습니다. **Battery** 센서를 확인하세요. 저전압 바이너리 센서는 2.5V(XTE는 10%) 이하에서 켜집니다.

## 증상과 조치

| 증상 | 실패 단계 | 확인 사항 | 조치 |
|---|---|---|---|
| 태그가 전혀 발견되지 않음 | `unreachable` | 라디오 수신 상태, 프록시 온라인 여부, 배터리 잔량 | 태그를 프록시 가까이 이동, 배터리 교체, `bluetooth_proxy.active: true` 확인 |
| 연결이 계속 실패함 | `connect` | 약한 RSSI(-85 dBm 이하), 프록시 연결 슬롯 소진 | 태그 근처에 프록시 추가 또는 프록시당 BLE 기기 수 분산 |
| 프로토콜 시작 전 세션 종료 | `session` | 설정된 프로토콜 또는 모델 불일치 | 물리 라벨과 진단 정보의 프리셋/모델 일치 여부 확인 |
| 핸드셰이크 / 인증 실패 | `auth` | 태그 미준비 상태 또는 미지원 펌웨어 | 일시적 지연은 재시도로 해결; 지속 시 프로토콜 지원 펌웨어 확인 |
| 이미지 전송 중단 | `transfer` | 전파 링크 품질, 패킷 손실, 낮은 RSSI | 실제 연결된 `via` 라디오 확인 및 거리 단축; 다음 재시도는 자동 감속 |
| 패널 리프레시 미확인 | `finish` | 대형 패널 리프레시 시간(7.5인치 이상은 수십 초), 저전압 | 실물 태그 화면 확인; 대형/저온 패널은 리프레시에 더 긴 시간이 소요됨 |
| 자동화는 실행되나 태그 불변 | `skipped` | Write Lock 스위치 켜짐 또는 중복 이미지 건너뜀 | Write Lock 스위치 끄기 또는 Prevent Duplicate Send 해제 |

### 상세 단계 분석

- **`unreachable`**: 어떤 라디오도 태그의 광고를 감지하지 못했습니다. Home Assistant에서 프록시/어댑터 연결 상태를 확인하고, 배터리를 교체하거나 거리를 좁히세요.
- **`connect`**: 링크 연결에 실패했습니다. RSSI와 `paths`를 확인하고, `slot` 오류 발생 시 프록시 연결 부하를 줄이세요.
- **`session`**: 연결 후 프로토콜 시작 전 세션이 종료되었습니다. [models.md](models.md) 및 진단 정보의 모델 프리셋 설정을 확인하세요.
- **`auth` (`failed_detail: handshake`)**: 이미지 전송 전 태그 응답 실패. 일시적인 경우 재시도로 복구되며 지속 시 펌웨어 호환성을 확인하세요.
- **`transfer`**: 이미지 전송 중 오류. 전파 링크 품질(`rssi`, `via`)을 확인하고 태그와 프록시 거리를 좁히세요.
- **`finish`**: 전송 후 완료 응답 미수신. 대형 패널 리프레시는 수십 초 이상 걸릴 수 있습니다.
- **`error: Attempt timed out after 600s …`** (`timed_out: true`): 전송 작업이 10분 제한을 초과함. 큐 고착을 방지하기 위해 즉시 재시도되지 않습니다.
- **`likely_cause_key: link_lost`**: 전송 중 링크 두절(범위 이탈, 배터리 급방전 등). 즉시 재시도됩니다.
- **`likely_cause_key: write_timeout`**: 조각 쓰기 타임아웃(10초 제한). 프록시 또는 어댑터를 재시작하세요.
- **`likely_cause_key: session.gatt_mismatch`**: 태그 GATT 서비스/특성이 프리셋과 불일치하거나 쓰기 크기가 너무 작음.

## 진단 및 로그

### 센서 진단

태그 기기 페이지(**설정 → 기기 및 서비스 → BLE ESL → 해당 태그**)의 *진단* 항목에서 다음 엔티티를 확인하세요:

- **Last Failure Time**: 마지막 쓰기 실패 시점. 속성에 `failed_stage`, `likely_cause`, `error`, 라디오 정보(`via`, `rssi`, `paths`), 단계별 타이밍이 기록됩니다.
- **Write Duration**: 최근 쓰기 소요 시간 및 동일한 세부 속성.
- **Failure Count**: 재로드 후 누적 실패 횟수.
- **Display In Sync** (바이너리): 마지막 렌더 이미지와 태그 수신 이미지가 일치하면 `on`.
- **Connectivity** (바이너리): 쓰기 작업 진행 중에만 `on`.

기기 페이지의 **진단 다운로드**(⋮ → *진단 다운로드*)에서도 `write_state.last_write`, `write_state.last_failure_write` 항목을 확인할 수 있습니다.

### 디버그 로깅

문제를 분석하려면 `configuration.yaml`에 다음 설정을 추가하세요:

```yaml
logger:
  default: warning
  logs:
    custom_components.ble_esl: debug
```

1회 쓰기를 재현한 후 디버그 설정을 제거하세요.

### 민감 정보 제거

Issues와 Discussions는 공개 공간입니다. 진단이나 로그를 공유하기 전에:
- `via` / `advertised_via`에 포함된 프록시/어댑터 MAC 주소를 `esp-proxy-1 (XX:XX:…)` 형태로 마스킹하세요.
- 엔티티 ID에 포함된 태그의 MAC 식별자(마지막 8자리)를 필요시 가리세요.
- 렌더링된 텍스트나 **Last Updated Content** 이미지의 개인 일정, 이름, 주소 등을 잘라내거나 가리세요.
- 디버그 로그의 토큰이나 내부 주소를 점검하세요.

## 문제가 계속되는 경우

이 통합의 [기존 Issues](https://github.com/eigger/hass-ble-esl/issues)를 이용하세요. 문의 시 다음 사항을 첨부해 주세요:

1. 태그 기기 페이지에서 다운로드한 **진단 파일** (Device Diagnostics JSON).
2. 화면 이상 시 **Last Updated Content** 이미지와 실물 태그 촬영 사진.
3. 액션 호출 실패 시 에러 메시지 전문 또는 자동화 실행 추적(Trace).
4. 사용 중인 라디오/프록시 모델 정보 (`via`).
