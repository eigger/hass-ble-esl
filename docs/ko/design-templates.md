# 디자인 템플릿

**[English](../design-templates.md)** | 한국어

> 영어 문서가 기준입니다. 내용이 다르면 [영어 원문](../design-templates.md)을 따릅니다.

> 템플릿을 고르는 디자이너 UI는 후속 변경에서 추가됩니다. 이 문서는 파일 형식과 API를 설명합니다.

디자인 템플릿은 완성된 ESL 디자인을 설명하는 YAML 파일입니다. imagespec 요소, 사용자가 바꿀 수 있는 몇 가지 값(글꼴, 색상, 시각 등), 그리고 선택적으로 디자인을 최신으로 유지하는 자동화를 담습니다. 디자이너에서 적용하면 일반 요소가 만들어져 자유롭게 편집할 수 있고, 저장된 결과는 템플릿을 참조하지 않습니다.

기본 제공 템플릿은 [`custom_components/ble_esl/designer/templates/`](../../custom_components/ble_esl/designer/templates)에 있고, 이 폴더의 `*.yaml`을 Home Assistant 시작 시 모두 읽습니다. 올바르지 않은 파일은 건너뛰며 경고(`Ignoring design template …`)가 로그에 남습니다.

> [`examples/`](../../examples) 폴더는 설명용이며 통합과 함께 설치되지 않습니다. 템플릿은 위 폴더에 넣어야 합니다.

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
      y: 10
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
| `string` | 문자열 | Jinja 문자열 안에 들어갈 수 있으므로 중괄호, 따옴표, 역슬래시, 줄바꿈 불가 |
| `number` | 숫자 | 선택적 `min` / `max` |
| `time` | `HH:MM` 또는 `HH:MM:SS` | `HH:MM:SS`로 저장 |
| `boolean` | true / false | |

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

테스트를 실행하세요. `tests/test_design_templates.py`는 모든 기본 템플릿을 읽어 여러 화면 크기와 색 조합에서 payload를 가져오고, 렌더링한 뒤 디자이너가 `0` 픽셀 차이로 재현하는지 확인합니다. 자동화도 Home Assistant로 검증합니다.

## API

디자이너 websocket 명령 `ble_esl/designer`에 `design_templates`(태그별 목록)와 `apply_design_template`(`template_id`, `parameters`, `existing`, `preview_variables`)이 있습니다. 후자는 가져오기 결과에 선택된 layout, 최종 parameter 값, 자동화 기본값이 든 `template` 블록을 더해 돌려줍니다. 이 기본값을 `automation` 액션의 `automation_defaults`로 넘기면 새 자동화가 미리 채워집니다.
