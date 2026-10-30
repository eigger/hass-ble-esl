# Designer translation glossary

The designer's UI text lives in `custom_components/ble_esl/designer/frontend/locales/`
(one file per language, English text as the key). Translations were added a few
keys at a time, which is how different words for the same thing crept in. To keep
one word per concept:

1. Before adding or changing a string, `grep` the same file for the concept
   (ESL, automation, entity, component, template, image, preview, unlink) and use
   the word that file already uses most.
2. When a variant is settled, add it to `FORBIDDEN_TERMS` in
   `tests/components/ble_esl/frontend/language.spec.js` so it cannot come back.

| Concept | Term used |
| --- | --- |
| The device | **ESL** in every language (not tag / label / etiqueta / Etikett …) |
| Preview modes | *Edit view* / *Rendered view* (pt-BR: *Modo de edição* / *Modo renderizado*, so *pré-visualização* stays "preview") |

| Language | automation | entity | component | template | image | preview | unlink |
| --- | --- | --- | --- | --- | --- | --- | --- |
| de | Automatisierung | Entität | Komponente | Vorlage | Bild | Vorschau | Verknüpfung aufheben |
| es | automatización | entidad | componente | plantilla | imagen | vista previa | desvincular |
| fr | automatisation | entité | composant | modèle | image | aperçu | dissocier |
| it | automazione | entità | componente | modello | immagine | anteprima | scollega |
| ja | オートメーション | エンティティ | コンポーネント | テンプレート | 画像 | プレビュー | リンクを解除 |
| ko | 자동화 | 엔티티 | 컴포넌트 | 템플릿 | 이미지 | 미리보기 | 연결 해제 |
| nl | automatisering | entiteit | component | sjabloon | afbeelding | voorbeeld | ontkoppelen |
| pl | automatyzacja | encja | komponent | szablon | obraz | podgląd | odłącz |
| pt-BR | automação | entidade | componente | modelo | imagem | pré-visualização | desvincular |
| ru | автоматизация | объект | компонент | шаблон | изображение | предпросмотр | отвязать |
| zh-Hans | 自动化 | 实体 | 组件 | 模板 | 图像 | 预览 | 取消关联 |
| zh-Hant | 自動化 | 實體 | 組件 | 範本 | 影像 | 預覽 | 取消關聯 |

**payload** stays the Latin word *payload* in every Latin-script and Chinese
language (it is the YAML key `payload:`); Japanese and Korean use the
transliteration (ペイロード, 페이로드).

**Link / unlink** are verbs on the same root in each language: de verknüpfen /
Verknüpfung aufheben, es vincular / desvincular, fr lier / dissocier, it
collega / scollega, ja リンク / リンクを解除, ko 연결 / 연결 해제, nl koppelen /
ontkoppelen, pl powiąż / odłącz, pt-BR vincular / desvincular, ru привязать /
отвязать, zh 关联 / 取消关联 (zh-Hant 關聯 / 取消關聯). *Link automation* is a verb
phrase, never a noun ("Automação de links").

Words that look like a variant but are not: a JSON *object* (de Objekt, pl obiekt,
ru объект) is not an entity; the tokens `{{ template }}` and `template_id` stay
as they are (the word *Jinja templates* itself is translated); *remove*/*delete*
are different actions from *unlink*.

The server's fixed error messages are translated by exact English text (see
`serverMessage` in `i18n.js`); `tests/components/ble_esl/test_designer_messages.py`
keeps that list in step with the Python code.
