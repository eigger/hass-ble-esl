# 사용 개요

**[English](../usage.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 원문](../usage.md)을 따릅니다.

README에 있던 사용 관련 상세 내용을 모은 문서입니다: e-paper 태그를 쓰는 이유, 첫 레이아웃 쓰기, 비주얼 에디터, 두 액션, 통합구성요소 옵션, imagespec 렌더러 위에 이 통합구성요소가 더하는 것. 액션·응답·엔티티 전체 레퍼런스는 [actions.md](../actions.md)(영어), Bluetooth 설정은 [bluetooth.md](bluetooth.md)에 있습니다.

## 왜 e-paper 태그인가?

**전자가격표시기(ESL)** 는 마트 선반에서 가격을 보여주는 그 디스플레이입니다: 자체 배터리와 블루투스 라디오가 달린 **e-paper**(e-ink) 화면이죠. e-paper는 그림이 *바뀔 때*만 전력을 쓰고, 정지 화면을 유지하는 데는 전력이 들지 않습니다. 그래서 배터리 하나로 수개월에서 수년을 버티고, 햇빛 아래에서도 인쇄물처럼 읽히며, 빛을 내지 않습니다.

콘센트가 없는 자리에 *그냥 붙어 있어야 하는* 정보에 딱 맞습니다: 문 앞의 회의실 캘린더, 현관의 오늘 날씨, 냉장고의 분리수거 요일, "누가 집에 있나" 보드, 3D 프린터 진행률, 수납함의 재고 라벨. 아무 데나 붙여 두고 충전은 잊으면 됩니다.

이 통합구성요소는 Home Assistant에서 BLE로 태그에 직접 이야기합니다. 레이아웃을 YAML로 적으면(텍스트, 아이콘, QR 코드, 차트, 이미지 — 엔티티에서 나오는 무엇이든) 태그가 그걸 보여줍니다.

## 첫 레이아웃

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
      "y": 10
      size: 40
```

몇 초 뒤 태그가 갱신됩니다. `dry_run: true`를 붙이면 보내지 않고 렌더링만 합니다 — 결과는 태그의 **Preview Content** 이미지 엔티티에 나타나므로, 패널을 소모하지 않고 레이아웃을 다듬을 수 있습니다.

레이아웃은 [imagespec](https://github.com/eigger/imagespec) 요소의 목록입니다 — 텍스트, 아이콘, 선, QR 코드, 진행 바, 게이지, 파이/막대 차트, 히스토리 플롯, 다운로드 이미지 — 그리고 어떤 값이든 엔티티를 참조하는 Jinja 템플릿이 될 수 있습니다. 지원 해상도별로 완성된 레이아웃은 [`examples/`](../../examples/README.md)(영어)에 있고, [Payload Editor](https://eigger.github.io/BLE_ESL_Payload_Editor.html)와 [Image Uploader](https://eigger.github.io/Gicisky_Image_Uploader.html) 웹 도구로 브라우저에서 초안을 만들 수 있습니다.

## 비주얼 에디터

![ESL 매니저 대시보드](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/manager/dashboard-ko.png)

**ESL Manager**는 모든 태그를 한눈에 보는 대시보드입니다. 별칭, 배터리, 마지막으로 전송에 성공한 이미지, 화면 동기화 여부, 최근 전송 결과와 소요 시간, 연결된 자동화를 보여 주며 검색, 필터, 정렬을 지원합니다. 카드에서 바로 디자이너나 태그를 그리는 자동화를 열 수 있습니다.

사이드바의 **ESL Manager**로 payload를 눈으로 보며 만듭니다. 요소를 끌어 옮기고 크기를 바꾸고 겹쳐 놓으며, [imagespec 요소](https://github.com/eigger/imagespec/blob/v1.1.0/docs/elements.md) 서른 가지(도형, 텍스트, QR / 바코드, 차트, 표 등)를 모두 추가해 각 필드를 편집할 수 있고, Jinja 템플릿도 쓸 수 있습니다. 미리보기, 태그로 보내는 이미지, 내보내는 **Payload YAML**(payload, 또는 템플릿을 쓴 그대로 둔 완성된 `ble_esl.write` 액션. 그래서 자동화가 센서를 따라갑니다)은 같은 렌더러가 그리는 같은 payload입니다. **Import YAML**은 이미 가진 액션의 payload를 디자이너로 가져오고, **Convert to elements**는 센서나 기존 컴포넌트를 평범한 요소로 바꿉니다. Bluetooth Send는 사용자가 요청할 때만 전송하며 아무것도 저장하지 않습니다. 디자인은 자동화에 보관되고, 미저장 작업은 브라우저 초안으로만 남습니다. 디자이너는 센서 변경 시 자동 전송하지 않습니다. 내보낸 액션으로 Home Assistant 자동화에서 갱신 시점을 설정하세요.

연결된 자동화 목록에서 **Edit automation design**으로 기존 `ble_esl.write` payload를 별도 편집 세션에서 열고, **Save automation**으로 저장할 수 있습니다. 최신 자동화 설정을 다시 읽어 선택한 액션의 `data.payload`만 바꿉니다. 선택 액션이 변경·중복되었거나 디자인이 유효하지 않으면 저장을 막으며, 저장은 Bluetooth 전송을 하지 않습니다. 세션을 나가면 원래 디자인과 실행 취소 기록을 복원합니다.

기존 YAML 액션도 그대로 쓸 수 있습니다. 전체 안내: **[디자이너 가이드](designer.md)**.

## 액션

두 액션 모두 표준 `target:`(태그 기기, 그 엔티티, 또는 태그가 속한 구역/층/레이블)을 받고 대상마다 차례로 씁니다.

| 액션 | 용도 |
|---|---|
| `ble_esl.write` | 항상 전송 (`dry_run` 제외) |
| `ble_esl.write_guarded` | 자주 발화하는 자동화용: 바뀌지 않은 이미지는 건너뛰고, **Write Lock** 스위치를 존중하며, 연속 호출을 디바운스 |

| 파라미터 | 기본값 | 설명 |
|---|---|---|
| `payload` | — | [imagespec 요소](https://github.com/eigger/imagespec/blob/main/docs/elements.md) 목록 (필수). 의도적으로 빈 화면을 보내려면 `[]` 사용 |
| `rotate` | `0` | `0`, `90`, `180`, `270` |
| `background` | `white` | `white`, `black`, `red`, `yellow` |
| `dry_run` | `false` | **Preview Content**에 렌더링만 |
| `debounce_override_ms` | 옵션 값 | `write_guarded` 전용: 이 호출의 디바운스를 덮어씀 (`0` = 즉시) |

두 액션 모두 `response_variable`로 태그별 결과를 돌려줄 수 있습니다. 전체 레퍼런스 — 사진·차트 디더링, 회전, 응답 데이터, 태그별 엔티티, 폰트: **[actions.md](../actions.md)** (영어).

## 옵션

**설정 → 기기 및 서비스 → BLE ESL → 구성**:

| 옵션 | 기본값 | 범위 | 설명 |
|--------|---------|-------|-------------|
| **Model** | — | 모델 목록 | 모델을 스스로 알리지 못하는 프로토콜(WOLINK, easyTag)에만 표시 |
| **Retry Count** | 3 | 1–10 | BLE 쓰기 실패 시 재시도 횟수 |
| **Prevent Duplicate Send** | 꺼짐 | 켬/끔 | 이미지가 바뀌지 않았으면 전송 생략 |
| **Debounce Delay (ms)** | 0 | 0–120000 | 쓰기 전 대기; 새 요청이 오면 대기 중인 요청은 취소 |

> [!TIP]
> 자주 발화하는 자동화라면 **Prevent Duplicate Send**나 **Debounce Delay**를 켜서 태그 배터리와 BLE 점유를 아끼세요. 전송 중에 실패한 쓰기는 다음 재시도에서 패킷 간격을 더 두고 보냅니다; 계속 실패하면 **Write Duration** 센서의 속성이 링크 문제인지 배치 문제인지 알려줍니다 — [troubleshooting.md](troubleshooting.md)를 보세요.

이 옵션은 BLE ESL 전용이며 Bluetooth 프록시 펌웨어 설정이 아닙니다.

## 페이로드와 렌더링

레이아웃은 **[imagespec](https://github.com/eigger/imagespec)** 이 렌더링합니다; 요소와 필드의 기준 문서는 그쪽입니다:

| 주제 | 링크 |
|-------|------|
| 미리보기 이미지가 있는 요소 예제 | [imagespec/docs/elements.md](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| 모든 요소 필드와 기본값 | [imagespec README — Element Reference](https://github.com/eigger/imagespec#element-reference--json-schema) |
| 레이아웃, 팔레트, LLM 작성 가이드 | [imagespec/docs/authoring.md](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) |
| 디더링 (요소 단위만) | [imagespec/docs/dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md) |

이 통합구성요소가 그 위에 더하는 것:

- **해상도와 팔레트**는 호출이 아니라 태그의 프리셋에서 옵니다. 팔레트 밖의 색은 가장 가까운 지원 색(BW, BWR, BWRY)으로 양자화됩니다.
- **회전** (`rotate: 90/180/270`)은 캔버스를 돌립니다; 출력 크기는 패널 크기 그대로입니다.
- **디더링**은 요소 단위입니다: 사진과 차트(`dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge`)에 `dither`를 붙이고, 텍스트에는 붙이지 마세요.
- **`plot`** 은 Recorder에서 히스토리를 읽습니다; **`dlimg`** 는 `/config/...` 경로, HTTP(S) URL, data URI를 받으며 Home Assistant 자체 권한으로 읽습니다. 그래서 `write`와 `write_guarded`는 관리자 전용입니다(자동화는 영향 없음).
- **폰트:** 기본은 `NotoSansKR-Regular.ttf`; `config/www/fonts/`에 `.ttf`를 넣고 이름으로 참조합니다. [fonts](../actions.md#fonts)(영어)를 보세요.
- 좌표를 손으로 찍기보다 `row` / `column` / `stack` 레이아웃을 쓰세요.

## 관련 프로젝트

- [imagespec](https://github.com/eigger/imagespec) — `payload:` 뒤에서 도는 렌더링 엔진
- [Stash](https://github.com/eigger/stash) — Home Assistant를 통해 ESL 태그에 라벨을 출력하는 셀프호스팅 가정 재고 관리자
- [hass-gicisky](https://github.com/eigger/hass-gicisky) — 보관 처리된 PickSmart 전용 전신 ([마이그레이션 가이드](migration.md))
