# 디자인 템플릿

갤러리에서 날씨, 일정, 스마트 홈, 라벨 분류로 템플릿을 필터링할 수 있습니다. 하나의 템플릿은 여러 분류에 속할 수 있으며, 분류가 없는 템플릿은 전체에 표시됩니다. YAML의 `categories`는 선택 사항입니다. 예: `categories: [weather, schedule]`. 사용 가능한 값은 `weather`, `schedule`, `smart_home`, `labels`입니다.


**[English](../design-templates.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 원문](../design-templates.md)을 따릅니다.

## 템플릿 사용하기

디자이너에서 왼쪽 패널 맨 위의 **Browse design gallery**(디자인 갤러리 열기)를 누릅니다. 갤러리에 디자인 목록이 실제 렌더러로 그린 이 태그용 미리보기와 함께 나오고(없는 기본 엔티티는 같은 도메인의 첫 엔티티로 대체), 태그 화면 크기에 맞게 layout이 *조정됨*인지 표시됩니다. 템플릿을 고르고 필요하면 parameter를 바꾼 뒤(모두 기본값이 있고, 입력하면 필드 위의 미리보기가 다시 그려짐):

- **Add to display**는 캔버스를 유지하고, **Replace display**는 새로 시작합니다. 결과는 편집 가능한 일반 요소입니다.
- **Replace and create automation**(`automation` 블록이 있는 템플릿, 쓰기 가능한 태그)은 **Create automation**도 엽니다. 템플릿의 실행 조건(예: *매일 12:00*)이 미리 채워져 있으며, 그 대화상자에서 **Create automation**을 누르면 저장됩니다.

**Add to display** 후에도 툴바의 **Create automation**을 쓸 수 있습니다. 마지막으로 적용한 템플릿의 실행 조건이 쓰이며, 그 디자인의 요소가 캔버스에 남아 있는 동안에만 유지됩니다(실행 취소, 교체, 가져오기, 요소 삭제 시 사라집니다).

디자인 템플릿은 완성된 ESL 디자인을 설명하는 YAML 파일입니다. imagespec 요소, 사용자가 바꿀 수 있는 몇 가지 값(글꼴, 색상, 시각 등), 그리고 선택적으로 디자인을 최신으로 유지하는 자동화를 담습니다. 디자이너에서 적용하면 일반 요소가 만들어져 자유롭게 편집할 수 있고, 저장된 결과는 템플릿을 참조하지 않습니다.

기본 제공 템플릿은 [`custom_components/ble_esl/designer/templates/`](../../custom_components/ble_esl/designer/templates)에 있고, 이 폴더의 `*.yaml`을 Home Assistant 시작 시 모두 읽습니다. 올바르지 않은 파일은 건너뛰며 경고(`Ignoring design template …`)가 로그에 남습니다.

> [`examples/`](../../examples) 폴더는 설명용이며 통합과 함께 설치되지 않습니다. 템플릿은 위 폴더에 넣어야 합니다.

## 기본 제공 템플릿

갤러리는 1.54~13.3인치 지원 태그의 가로·세로 해상도에 맞는 레이아웃을 선택합니다. 작은 화면은 핵심 값을 크게 표시하고, 기존 템플릿은 4.2인치(`date`, `weather_forecast`) 및 5.8인치부터 가로·세로 화면 모두에서 세부 정보를 더 보여줍니다. 기존 갱신 주기는 유지됩니다.

| 템플릿 | 기본 정보 | 큰 화면에서 추가되는 정보 | 자동화 |
|---|---|---|---|
| `date` | 월/일과 아래의 요일(주말 색상) | 연도, ISO 주차와 이번 주 날짜(4.2인치부터) | 매일 12:00 |
| `wifi` | 제목과 안내 문구가 있는 Wi-Fi QR 코드(WPA, WPA3/SAE, WEP, 개방, 숨김 네트워크) | 공개 네트워크의 이름과 보안 방식 | 없음 |
| `message` | 화면에 맞춰 줄어드는 큰 글자(기본 한 줄) | 보조 문구 선택 입력 | 없음 |
| `color_check` | 검정, 흰색, 빨강, 노랑 견본 | 해상도 및 1·2·4픽셀 선 견본 | 없음 |
| `weather_now` | 선택한 `weather` 엔티티의 아이콘, 온도, 상태, 오늘의 최고·최저와 상단 또는 하단 바(없는 값은 `—`) | 4인치부터 체감온도·습도·풍속·강수확률, 5.8인치부터 3시간 간격 예보 줄 | 10/15/30분마다 |
| `weather_forecast` | `weather` 엔티티의 앞으로 3일 일별 예보를 열로 표시: 요일, 아이콘, 최고/최저 (예보를 가져오기 전에는 `—`) | 4.2인치부터 위쪽에 오늘 날씨, 아래에 날마다 한 줄: 강수확률과 최저~최고 기온 막대(5일, 세로로 긴 태그는 6일, 5.8인치부터 7일) | 1/3/6시간마다 |
| `weather_outdoor` | 외출 날씨. 4인치 미만은 큰 현재 기온과 비·눈 알림/시각 표시(`3.5인치`부터 최저·최고 추가) | 4.2인치부터 7일 예보, 7.5인치부터 시간대별 예보 | 매시 정각 |
| `weather_commute` | 외출 날씨 브리핑. 3인치 미만은 판정 배너(우산·눈·일교차·강풍)와 큰 온도·최저/최고, 3~4인치의 가로로 넓은 태그는 배너 아래 짧은 시간대별 줄 | 배너, 3시간 간격 6~8칸 시간대별 예보와 기온 추세, 체감·습도·바람·일몰 | 1/3/6시간마다 |
| `sensor_card` | `sensor` 엔티티의 아이콘, 제목, 값과 단위 (제목을 비우면 엔티티 이름, 숫자는 소수 첫째 자리까지, 선택적 경고 기준값 강조) | 마지막 갱신 시각과 선택한 보조 센서 값 | 5/10/15/30분마다 |
| `calendar_next` | `calendar` 엔티티의 진행 중이거나 다음 일정: 제목, 날짜와 시간, 장소 (기본 엔티티 속성 폴백 지원) | `calendar.get_events` 기반 최대 3개 일정 또는 종료 시각·설명 | 일정이 바뀔 때, 10/15/30분마다 |
| `print_progress` | 센서 3개로 만드는 3D 프린터 진행률 막대와 퍼센트, 상태, 종료 시각 (진행률은 0~100으로 제한) | 예상 남은 시간 및 선택적 노즐/베드 온도 | 1/5/10/15분마다, 상태가 바뀔 때 |
| `date_weather` | 오늘 날짜와 요일, `weather` 엔티티의 아이콘, 온도, 상태 | 체감온도, 습도, 풍속 | 10/15/30분마다 |
| `countdown` | 정해진 날짜까지 남은 일수(`D-12`, `D-Day`, `D+3`)와 제목. 지정한 일수 이내와 날짜가 지난 뒤에도 강조 색상 (잘못된 날짜는 `--`) | 목표일의 요일과 주·일 단위 기간 | 매일 00:05 |
| `indoor_climate` | 큰 실내 온도·습도 및 쾌적/환기 상태 안내 | 온도·습도·선택 CO2·초미세먼지 진행률 막대 카드 및 환기 권장 배너(4.2인치 이상) | 5/10/15/30분마다 |
| `calendar_weather` | 큰 현재 날씨 온도·다음 일정 1건(엔티티 속성, `3.5인치`부터 날짜 추가) | 오늘 최저/최고·4일 일별 예보·강수확률 및 다가오는 일정 최대 4건(`calendar.get_events`) | 10/15/30분마다 |
| `home_presence` | 큰 가족 재실 수·현관문 상태 안내(`3.5인치`부터 재실 이름 요약 추가) | 구성원 4명 카드(상태·마지막 변경 시각)와 현관 출입문 열림/닫힘 배너(4.2인치 이상) | 5/10/15/30분마다 |
| `energy_power` | 큰 실시간 전력·부하 상태·오늘 사용량 | 목표 대비 부하 막대, 오늘 사용량·태양광 발전 카드 및 절전 안내 배너(4.2인치 이상) | 1/5/10/15분마다 |
| `ev_charging` | 큰 전기차 배터리 잔량·충전 상태·주행 가능 거리(`3.5인치`부터 충전 전력 추가) | 충전 진행률 막대, 기준 안내, 주행 거리·충전 전력 카드 및 상태 상세 배너(4.2인치 이상) | 5/10/15/30분마다 |
| `appliance_status` | 4인치 미만은 우선 가전 이름(`오류`>`완료`>`동작`)과 큰 상태 텍스트·아이콘 표시 | 최대 3대 가전별 카드(남은 시간·마지막 변경 시각)와 완료·오류 알림 배너(4.2인치 이상) | 1/5/10/15분마다 |

디자이너는 일반 payload를 저장하므로, 서비스 응답은 payload 안의 템플릿이 직접 읽습니다. `weather_now`, `weather_forecast`, `weather_commute`, `calendar_weather`는 `weather.get_forecasts`(`daily`, `hourly`)의 `response_variable`인 `fc`(`weather_now`와 `weather_commute`는 `fc_hourly`도)를 읽고, 5.8인치 이상 `calendar_next` 및 4.2인치 이상 `calendar_weather` 레이아웃은 `calendar.get_events`의 `response_variable`인 `events`를 읽습니다(작은 태그이거나 `events`가 없으면 캘린더 엔티티 속성으로 자동 폴백). 디자이너는 미리보기 시 해당 엔티티의 실제 일별·시간별 예보나 캘린더 일정을 조회해 그리며, 자동화를 만들거나 업데이트할 때 필요한 조회 단계를 함께 추가합니다. 반복문으로 가변 길이 요소를 만드는 예제는 템플릿이 아닙니다. 템플릿은 고정된 payload를 담기 때문입니다(따라서 `home_presence`는 최대 4명까지 고정 슬롯으로 구성됩니다). `weather_now`처럼 엔티티 하나는 parameter가 될 수 있습니다.

외출 날씨는 선택한 날씨 엔티티의 일별·시간별 예보를 사용합니다. 가져올 수 없는 항목은 `—`로 표시합니다. 10.2·13.3인치에서 오늘 예상 적설을 제공하는 센서를 입력하면 양수일 때 예상 강수량 자리에 표시합니다. 일몰은 `sun.sun`에서 가져옵니다.

## 나만의 템플릿

템플릿 파일을 `<config>/ble_esl/templates/*.yaml`에 넣으면 다음에 갤러리를 열 때 *내 템플릿*으로 표시됩니다(재시작 불필요). 올바르지 않은 파일은 로그에 경고를 남기고 건너뛰며, 기본 제공 템플릿의 `id`는 재사용할 수 없습니다.

디자인에서 만들려면 디자이너에서 디자인을 만든 뒤 **Browse design gallery**를 열고 **현재 디자인을 템플릿으로 저장**(Save current design as a template)에 이름을 입력해 **템플릿으로 저장**(Save as template)을 누르세요. 현재 화면 크기만 layout으로 가진 파일이 위 폴더에 만들어집니다. 저장하지 않은 편집 내용도 포함되고 요소의 템플릿(Jinja)은 그대로 유지됩니다. 같은 이름으로 다시 저장하거나, 이름이 기본 제공 템플릿이나 폴더에 이미 있는 파일(로드되지 않는 파일 포함)과 겹치면 덮어쓰지 않고 새 id(`이름_2`)가 붙습니다. `overwrite`와 함께 명시한 `template_id`만 해당 id의 파일을 덮어씁니다. 갤러리는 열 때마다 폴더를 다시 읽습니다. 이후 파일을 직접 고쳐 `parameters`(값을 `${name}`으로 교체), 다른 layout, `automation` 블록을 추가하세요.

텍스트에 `${…}`가 들어 있는 디자인은 parameter로 읽히므로 이렇게 저장할 수 없습니다.

## 파일 형식

```yaml
template: 1                  # 형식 버전, 항상 1
id: date                     # 소문자/숫자/밑줄, 고유해야 함
name: { en: Date label, ko: 날짜 라벨 }   # 문자열 또는 언어별 맵
description: { en: …, ko: … }
background: white            # black | white | red | yellow (태그가 못 내면 white)

parameters:                  # 사용자가 바꿀 수 있는 값
  font:
    type: font
    default: GmarketSansTTFBold.ttf
    label: { en: Font, ko: 글꼴 }
  time:
    type: time
    group: automation        # 자동화에서만 사용
    default: "12:00:00"

layouts:                     # 화면 크기별 payload
  "250x128":
    - type: text
      value: "{{ now().strftime('%m/%d') }}"
      font: ${font}
      anchor: mt
      x: 125
      "y": 10
      size: 45

automation:                  # 선택
  alias: 날짜 라벨
  triggers:
    - trigger: time
      at: ${time}
  mode: single
```

### layouts

`layouts`의 각 키는 `가로x세로`이고, 값은 `ble_esl.write`의 `payload:`에 넣는 요소 목록과 같습니다([actions](../actions.md) 참고). 절대 좌표를 쓰고 요소는 최대 100개입니다. Jinja는 그대로 보존되므로 `{{ now() }}`는 자동화가 실행될 때마다 계산됩니다.

해당 크기의 layout이 없으면 가장 가까운 layout을 균등하게 확대/축소하고 가운데로 맞춥니다. 모든 숫자는 픽셀 길이로 보고 배율을 곱하며(외곽선 두께처럼 양수인 길이는 1 아래로 줄지 않음), 횟수·각도·데이터·한계값(`x_repeat`, `y_repeat`, `rotation`, `start_angle`, `end_angle`, `max_lines`, `min`, `max`, `min_value`, `max_value`, `progress`, `values`, `rows`, `grow`, `border`, 바코드의 mm 단위 키 `module_width` 등)은 제외합니다. 결과에는 `scaled: true`가 표시됩니다. polygon `points`가 있는 layout은 group 안에 있어도 확대/축소할 수 없으므로 크기마다 전용 layout이 필요합니다. 중요한 크기는 전용 layout을 작성하세요. 숫자가 아니라 템플릿인 값은 확대/축소하지 않습니다.

### parameters

layout과 automation 안의 `${name}`은 요소를 가져오기 전에 값으로 치환됩니다. Jinja `{{ }}`는 건드리지 않습니다. `size: ${size}`처럼 문자열 전체가 참조이면 값의 타입이 유지되고, 문장 속 참조는 문자열이 됩니다. 모든 `${…}`는 선언된 parameter여야 합니다.

| `type` | 값 | 비고 |
|---|---|---|
| `font` | 파일 이름 | 통합의 `fonts/` 또는 `www/fonts`에 있어야 함 |
| `color` | `black`, `white`, `red`, `yellow` | 태그가 못 내는 색은 `black`으로 대체 |
| `select` | `options` 중 하나 | `options: [a, b]` 필수 |
| `string` | 문자열 | Jinja 문자열 안에 들어갈 수 있으므로 중괄호, 따옴표, 역슬래시, 줄바꿈 불가. 선택적 `forbidden: ";:,"`로 추가 금지 문자, `min_length`로 최소 길이 지정 |
| `number` | 숫자 | 선택적 `min` / `max` |
| `time` | `HH:MM` 또는 `HH:MM:SS` | `HH:MM:SS`로 저장 |
| `boolean` | true / false | |
| `entity` | `weather.home` 같은 엔티티 id | 선택적 `domain: weather`로 범위를 제한(갤러리가 해당 엔티티를 제안). `domain`이 있을 때만 갤러리가 해당 엔티티를 제안하며, 기본값이 이 시스템에 없으면 첫 번째 일치 엔티티를 미리 채웁니다. 엔티티가 없으면 적용이 실패하므로 통합을 먼저 설정하세요 |

모든 parameter에는 `default`가 필요하므로 아무것도 묻지 않고 적용할 수 있습니다. `label`은 선택이며 문자열 또는 언어별 맵입니다. `group: automation`은 자동화에서만 쓰는 값이며 디자인에서 참조할 수 없습니다.

### automation

`automation`은 새 자동화의 기본값(alias가 없으면 태그 이름 사용)으로 alias, `triggers`(1개 이상), `conditions`, `mode`, `description`을 채웁니다. `ble_esl.write` 액션은 현재 디자인에서 평소처럼 추가되므로 템플릿에 쓰지 않습니다. 저장할 때 Home Assistant가 자동화를 검증합니다.

매일 정오에 갱신:

```yaml
automation:
  alias: 날짜 라벨
  triggers:
    - trigger: time
      at: ${time}
```

## 템플릿 검증

테스트를 실행하세요. `tests/components/ble_esl/test_design_templates.py`는 모든 기본 템플릿을 읽어 여러 화면 크기와 색 조합에서 payload를 가져오고, 렌더링한 뒤 디자이너가 `0` 픽셀 차이로 재현하는지 확인합니다. 자동화도 Home Assistant로 검증합니다.

## API

디자이너 websocket 명령 `ble_esl/designer`에 `design_templates`(태그별 목록)와 `save_design_template`(`name`, 선택적 `template_id`, `overwrite`; 디자인을 사용자 폴더에 저장), `preview_design_template`(`template_id`, `parameters`; 태그용 PNG를 그리기만 하고 가져오지 않음), `apply_design_template`(`template_id`, `parameters`, `existing`, `preview_variables`)이 있습니다. `apply_design_template`은 가져오기 결과에 선택된 layout, 최종 parameter 값, 자동화 기본값이 든 `template` 블록을 더해 돌려줍니다. 이 기본값을 `automation` 액션의 `automation_defaults`로 넘기면 새 자동화가 미리 채워집니다.
