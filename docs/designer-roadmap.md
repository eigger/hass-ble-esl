# ESL Designer 로드맵과 인수인계

> 내부 작업용 문서입니다(사용자용 안내는 [designer.md](designer.md)). 다른 에이전트나 다음 작업자가 이어서 작업할 수 있게 현재 상태, 지켜야 할 규칙, 겪은 함정, 남은 일을 한곳에 적었습니다. 기준일 2026-10-02, `main`은 PR #90까지 반영, 릴리스는 0.14.1 이후 아직 없음.

## 1. 방향

디자이너는 시안이고, 실제로 동작하는 것은 자동화입니다. 그래서 두 가지가 최우선입니다.

1. **payload를 가장 쉽게 꺼낼 수 있어야 합니다.** 미리보기, 태그에 쓰는 이미지, 내보낸 YAML은 같은 payload를 같은 imagespec 렌더러가 그린 것이어야 합니다.
2. **그리기가 쉬워야 합니다.** imagespec 요소를 모두, 필드 하나까지 편집할 수 있어야 합니다.

## 2. 현재 상태 (`main`)

| PR | 내용 |
|---|---|
| #85 | 디스플레이를 payload 전체의 imagespec 단일 렌더로 만듦(요소별 합성 폐지), **Payload YAML**, `fa:` 아이콘 수정, CI를 lint / test / editor 잡으로 분리 |
| #86 | imagespec 요소 30종 추가(`designer/specs.py`), `imagespec.specs()`로 자동 생성되는 인스펙터, 프레임에서 위치 파생, 레이어는 요소가 실제로 그린 영역 |
| #87 | **Keep templates**: imagespec 요소의 Jinja를 그대로 내보내기(`live_payload`) |
| #88 | **Import YAML**(`importer.py`): 기존 payload를 요소로, 픽셀 차이 보고, 별칭 거부, 100개 한도 |
| #89 | **Convert to elements**: 기존 컴포넌트를 imagespec 요소로, 센서 값은 센서를 따라가는 템플릿 |
| #90 | `docs/designer.md`, `docs/ko/designer.md` |

버전은 `manifest.json`이 0.14.1입니다. 위 PR들은 아직 릴리스되지 않았습니다(릴리스는 사용자가 결정; 이 저장소의 방식은 `Release X.Y.Z` 커밋이 manifest 버전만 올리고, 노트는 요약 인용문과 `--generate-notes --notes-start-tag <이전>`).

## 3. 구조 지도

### 서버 (`custom_components/ble_esl/designer/`)

| 파일 | 역할 |
|---|---|
| `__init__.py` | `Designer`(저장, 자동 갱신, 렌더 잠금)와 웹소켓 명령 `ble_esl/designer`. 액션: `list` `specs` `save` `preview` `export` `import_yaml` `convert` `send` `templates` `save_template` `preview_template` |
| `layout.py` | 기존(v1) 요소 스키마와 `compile_payload`(요소 → imagespec payload), `live_payload`, `validate`, `validate_spec`, 센서 템플릿 |
| `specs.py` | **imagespec 요소의 핵심**: `GEOMETRY`(타입별 위치 역할), `EXAMPLES`, `spec_payload`(프레임 → payload), `from_payload`(역변환), `describe()`(편집기용 스키마), `resolve_templates`, `templates_in`, `frozen_corners` |
| `rendering.py` | `snapshot_layers`(템플릿을 한 번만 평가), `element_layer`, `render_document` |
| `export.py` | `export_yaml`, `plain()`(HA의 list/str 서브클래스를 YAML이 쓸 수 있게), `template_syntax` |
| `importer.py` | `parse`(별칭 거부, 256K자), `elements_from`, `payloads`, `different_pixels`, `value_template`, `convert` |
| `frontend/` | `panel.js`(약 2100줄), `spec-editor.js`(스펙 기반 인스펙터), `yaml-dialog.js`, `import-dialog.js`, `model.js`, 기존 컴포넌트용 `component-editor.js` `dynamic-fields.js`, `icons.json` |

### 데이터 모델

- 요소 타입: 기존 v1 타입(sensor, text, icon, image, 도형, progress_bar, gauge, conditional_icon)과 `imagespec`.
- `imagespec` 요소는 `spec`(위치 키를 뺀 순수 imagespec 요소)과 프레임(x, y, width, height)을 저장합니다. 위치를 나타내는 키는 저장하지 않고 `spec_payload`가 프레임에서 파생합니다. 역할: `box`, `line`, `circle`, `rect`, `icon`, `midline`, `origin`, `points`(퍼센트).
- 문서 한도는 요소 100개(`layout.DOCUMENT`).

### 테스트와 데모

- `tests/test_designer.py`, `tests/test_designer_specs.py`(요소 30종 × 프레임, 왕복, 내보내기, 가져오기, 변환), `tests/frontend/editor.spec.js` + `demo.html`(Playwright).
- `scripts/designer_demo.py`: 데모 서버(포트 8765). 실제 HA 없이 실제 렌더러를 씁니다.

## 4. 지켜야 할 불변식

이 중 하나가 깨지면 기능이 거짓말을 하게 됩니다. 테스트가 각각 지키고 있습니다.

1. 미리보기 == 태그에 쓰이는 이미지 == 내보낸 YAML을 렌더한 결과(픽셀 단위).
2. 요소별 레이어를 쌓은 결과 == 정확한 이미지(디더 없는 경우). 레이어는 요소가 그린 영역으로 잘라내며 프레임 밖으로 나가도 유지합니다.
3. 템플릿은 미리보기 한 번에 **한 번만** 평가합니다(`snapshot_layers`). 전체 payload는 요소별 payload를 이어 붙인 것입니다.
4. 템플릿 렌더는 **이벤트 루프**에서, executor에서는 이미 해석된 payload만 그립니다(HA 계약. 디버그 모드에서 검사됨).
5. 프레임 → payload → 프레임 왕복이 모든 타입에서 같은 payload를 만듭니다(`from_payload`).
6. 선택 박스와 핸들은 리사이즈 중에도 포인터에 붙어 있습니다(`visibleBounds`, `layerImage`).

## 5. 작업 방식 (지켜 온 절차)

- **브랜치 → PR 묶음 → Opus 서브에이전트 리뷰를 "지적 없음"이 될 때까지 반복 → CI 통과 → squash 머지.** 머지는 사용자가 "CI 확인하고 통과하면 머지"라고 말했을 때만 했습니다. 릴리스, imagespec 같은 외부 저장소 변경, PyPI는 항상 사용자 승인이 필요합니다.
- 리뷰 요청에는 무엇을 검증할지, 읽기 전용이라는 것, 8765 서버를 건드리지 말 것을 적었습니다.
- 커밋 끝에 `Co-Authored-By: Claude …`, PR 본문 끝에 `🤖 Generated with [Claude Code](…)`.

### 로컬 환경

- 테스트는 **WSL venv**에서: `wsl -e bash -lc 'source ~/.venv-ble-esl/bin/activate; cd /mnt/d/Source/Github/hass-ble-esl && python -m pytest tests/ -q -p no:cacheprovider'`. 린트는 `python -m ruff check/format custom_components tests docs scripts`(핀된 버전).
- 환경이 낡으면 먼저 확인: `blesession`은 `D:\Source\Github\blesession`의 editable 설치라 manifest 버전과 같아야 하고(`git fetch --tags && git merge --ff-only origin/main`), `imagespec`은 manifest 핀과 같아야 하고(현재 0.5.0), CI처럼 `python scripts/ha_component_requirements.py frontend panel_custom websocket_api`로 프런트엔드 의존성을 설치해야 합니다.
- WSL의 `git status`는 CRLF 때문에 전부 수정으로 보입니다. 상태와 diff는 Windows git으로 보세요.
- Playwright는 로컬에 없습니다(CI가 돌립니다). 프런트엔드는 데모 페이지에서 포인터 이벤트를 직접 보내 확인하고 spec은 CI용으로 씁니다. 데모는 gitignore된 `.claude/launch.json`에 다음을 두면 열립니다.

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "designer-demo",
      "runtimeExecutable": "wsl",
      "runtimeArgs": ["-e", "bash", "-lc", "source ~/.venv-ble-esl/bin/activate && cd /mnt/d/Source/Github/hass-ble-esl && python scripts/designer_demo.py"],
      "port": 8765
    }
  ]
}
```

JS는 새로고침만으로 반영되고, Python을 바꾸면 서버를 다시 시작해야 합니다.

### 겪은 함정

- 셸 heredoc에 `\n` 같은 이스케이프를 쓰면 의도와 다르게 바뀝니다. 파일은 Write 도구로 만들거나, 파이썬 스크립트 파일로 패치하세요.
- 데모 서버의 상태(저장된 센서 템플릿)는 테스트끼리 공유됩니다. 센서를 다루는 Playwright 테스트는 먼저 `POST /reset`을 하세요.
- 데모 서버는 실패한 명령을 HA처럼 메시지(400)로 돌려줍니다. 서버 로그의 트레이스백은 일부러 만든 오류가 아닌 한 진짜 문제입니다.
- `inline editing still gets a caret…` 테스트는 에뮬레이션 타이머와 타자가 겹쳐 간헐 실패했습니다. 클릭 뒤 대기를 넣어 고쳤으니, 다시 흔들리면 이 경합을 의심하세요.
- 같은 브라우저 패널을 서브에이전트와 공유하면 탭이 바뀝니다. 확인은 별도 탭에서 하세요.

## 6. 앞으로의 일

### 6.1 공용 편집기 (결정 대기)

사용자는 다른 컴포넌트에서도 쓸 수 있는 공용 편집기를 원합니다. 이미 있는 것들:

| 편집기 | 구성 | 스키마 |
|---|---|---|
| 이 통합의 디자이너 | HA 패널(JS)과 Python 백엔드 | `imagespec.specs()`에서 자동 생성 |
| `eigger.github.io/imagespec-editor` | 순수 JS 웹 편집기(`core.js`) | 손으로 관리, 이미 imagespec과 어긋남 |
| `hass-imagespec-card` | TypeScript/Lit Lovelace 카드, 설계만 있음(`docs/ARCHITECTURE.md`) | 손으로 관리(`schema/elements.ts`) |
| `hass-niimbot` | 자체 편집기 | 별도 |

**추천 순서:**

1. **imagespec 0.6에 편집기 계약을 올립니다.** `spec_payload`/`from_payload`(프레임 ↔ payload), `describe()`, 요소별 레이어 렌더링, 편집기용 스키마 JSON. 순수 로직이라 HA에 의존하지 않습니다(`resolve_templates`는 HA 쪽에 두고 함수로 주입). 그러면 웹 편집기, 카드, 디자이너가 같은 스키마를 씁니다.
2. **이 패널을 제자리에서 모듈화합니다.** 서버와 대화하는 부분을 "백엔드 어댑터" 인터페이스 뒤로 뺍니다(옮기지는 않음). 속성 편집기, YAML과 가져오기 다이얼로그, 레이어와 캔버스 로직이 HA 전용 코드(`ha-entity-picker`, `ha-icon-picker`, `hass.states`)와 분리되어야 합니다.
3. **그다음에** 일반 UI를 카드 저장소나 패키지로 옮기고, 이 통합은 빌드한 파일을 가져다 씁니다.

하지 않을 것: 디자이너 코어 전체를 imagespec에 넣기, JS를 Python wheel에 싣기.

**사용자의 결정이 필요한 것:**

1. imagespec 0.6으로 시작해도 되는지(imagespec 저장소 작업, PyPI 릴리스, `ble_esl` `niimbot` `gicisky`의 핀 변경).
2. 공용 UI의 집: `hass-imagespec-card`(TypeScript, 빌드 있음) 또는 이 저장소의 순수 JS 모듈.
3. 가장 먼저 붙일 소비자: `hass-niimbot` 또는 카드.

### 6.2 작은 후속 작업

리뷰에서 나왔고 머지를 막지 않아 남겨 둔 것들입니다.

- `export.plain()`이 `set` 타입을 처리하지 않습니다(렌더 결과가 set인 템플릿이면 YAML 직렬화 실패).
- 꼭짓점에만 템플릿이 있는 polygon 문서에서도 `Keep templates`가 나타납니다. 남는 템플릿이 없으면 `live_payload`가 `None`을 돌려주는 편이 맞습니다.
- 체크박스 문구 "Keep templates (values follow the sensors)"가 안내문보다 범위를 넓게 말합니다.
- 센서 이름이나 라벨에 `{#` 같은 템플릿 구문이 있으면 그 텍스트가 변환에서 통째로 빠집니다(`{% raw %}`로 감싸 보존할 수 있음).
- 단위 없는 문자열 센서가 나중에 숫자처럼 보이는 상태가 되면 HA가 숫자로 읽어 표시가 달라집니다.
- 반투명 PNG(`dlimg`)는 드래그 중 레이어 가장자리가 조금 다르게 보입니다(흰/검정 렌더로 알파를 계산하는 방식의 한계).
- `dlimg`와 `plot`은 미리보기마다 세 번 실행됩니다(전체 1 + 레이어 흰/검정 2).
- 다이얼로그 탭에 방향키 이동과 `aria-controls`가 없습니다.
- 원래부터 있던 README의 `Bluetooth Send` 표기와 가이드의 `Send to tag`가 다릅니다.
- 파일 이름 질문: 번역 문서는 `docs/ko/<같은 이름>.md` 규칙이고 이 문서들도 따랐습니다. `.ko` 접미사로 바꾸려면 기존 문서도 함께 옮기는 별도 PR이 맞습니다.

### 6.3 하지 않기로 한 것

- 센서, 조건부 아이콘, 날씨 예보 같은 기존 컴포넌트의 동작 전체를 Jinja로 번역하는 것. 정확하지 않은 번역보다 **Convert to elements**(원래와 같은지 픽셀 수로 알려 줌)가 안전합니다.
- 흐름 배치(`y` 없는 요소), 대각선, 템플릿으로 계산하는 위치를 가져오기에서 배치하는 것.

## 7. 알아 둘 외부 사실

- `imagespec` 0.5.0 공개 API: `specs()`, `get_spec()`, `build_json_schema()`, `validate()`, `render(strict=True)`, `known_types()`. `Field`에는 kind, required, default, enum, 중첩 fields, `positioned`(stack 자식용)가 있고 **위치 역할 정보는 없습니다**(그래서 `GEOMETRY` 표가 이 저장소에 있습니다).
- `row`와 `column`은 `stack`의 별칭이라 디자이너에는 `stack` 하나로만 있습니다.
- `imagespec.validate()`는 선언되지 않은 키를 오류로 봅니다. 디자이너 메타데이터를 요소 dict에 섞으면 안 됩니다.
- 숫자와 불리언 필드는 템플릿 문자열을 받습니다. HA 자동화에서 `data:`의 템플릿은 `parse_result`로 렌더되어 `"21.5"`가 숫자 21.5가 됩니다(디자이너의 `resolve_templates`도 같은 방식).
