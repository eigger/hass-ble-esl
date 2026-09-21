# Troubleshooting

English | **[한국어](ko/troubleshooting.md)**

When a label does not update, the integration has usually already recorded why. This page is the order to look in: first the two sensors that hold the last write's breakdown, then the cases those sensors cannot see, then what to attach to an issue.

## Where to look

Open the tag's device page (**Settings → Devices & services → BLE ESL → the tag**). Under *Diagnostic* there are three entities to read, in this order:

| Entity | What it tells you |
|---|---|
| **Last Failure Time** | When the last write **failed** (every retry exhausted). Its *attributes* are the breakdown of that failed write — `failed_stage`, `likely_cause`, `error`, the radio (`via`, `rssi`, `paths`) and the stage timings. They stay until the next failure, so a failure from last night is still readable after this morning's writes succeeded. |
| **Write Duration** | Seconds of the **most recent** write, success or not. Its *attributes* are the same breakdown for that attempt. Use it when the write you are debugging is the last one. |
| **Failure Count** | How many writes have failed since the integration was (re)loaded. Rising while labels look fine means writes are failing inside an automation nobody is watching. |

To see the attributes: click the entity → ⋮ → **Attributes**, or in **Developer tools → States** search for the entity. In a template: `{{ state_attr('sensor.<brand>_<id>_last_failure_time', 'likely_cause') }}` — e.g. `sensor.gicisky_a1b2c3d4_…` for a PickSmart tag, `sensor.zhsunyco_a1b2c3d4_…` for WOLINK / easyTag, `sensor.poshiji_a1b2c3d4_…` for XTE (the id is the last 8 hex digits of the MAC).

The same breakdown is in the **diagnostics download** (device page → ⋮ → *Download diagnostics*, `write_state.last_write` and `write_state.last_failure_write`) and, when an automation asks for it, in the action's response (`response_variable` → `timing`).

Two more entities help, but read them for what they are:

- **Display In Sync** (binary) — on when the last image *rendered* is the one the tag *received*. Off after a `dry_run`, or after a write that failed following a new render; `unknown` until the tag has received an image at all. It does not know what the panel physically shows.
- **Connectivity** (binary) — on **while a write is in progress**, from the first attempt to the final result, including connection retries; off otherwise. It is not "the tag is nearby", nor "the link is up".

## Reading a failure

Start with `failed_stage` on Last Failure Time: it says how far the attempt got. `likely_cause` is a one-sentence reading of the stage, the error text and the radio situation; `error` is the exact message.

### `unreachable`

No radio currently sees the tag's advertisement; nothing was tried.
- *Check:* `error` says *out of range or adapter down*. Is the proxy/adapter itself up in HA?
- *Do:* Move closer, replace the battery (see the **Battery** sensor), check the proxy is online.

### `connect`

The link never came up (the tag advertised but did not accept a connection).
- *Check:* `rssi` and `paths` (how many radios reach the tag). `error` with *slot* = the proxy's connection slots are all in use.
- *Do:* Weak `rssi` (below about −85 dBm): move the tag or add a proxy near it — with `paths: 1` there is also no other radio to fall back to. *slot*: fewer BLE devices per proxy, or another proxy. Otherwise usually transient — the retries cover it.

### `session`

Connected, but the tag dropped or refused the session before the protocol started.
- *Check:* Does it repeat every time?
- *Do:* Once: ignore. Every time: the protocol or model may not match — check the preset in the diagnostics and the model table in [models.md](models.md).

### `handshake`

The tag did not answer, or answered wrongly, before any image data was sent.
- *Check:* PickSmart `start_probes: 3` = it never answered START. WOLINK *device error 5* = authentication refused. *No response … after command 0x01* (XTE) = no reply to the size command.
- *Do:* Unanswered: the tag was not ready yet — transient, retries cover it; if constant, the tag firmware is not one this backend knows. Auth refused: not a WOLINK tag, or different firmware. Wrong answer: wrong protocol/model.

### `transfer`

Failed while sending the image data. This is the one case that points at link quality.
- *Check:* `resends` / `round_trip_ms` (PickSmart), `sends` vs `parts` (how far it got), `chunk_size` (XTE: 20 means the proxy only allows tiny writes), `rssi`, `via` (which radio).
- *Do:* Move the tag or the proxy it actually used (`via`), or add one. The next retry is automatically paced slower (`pacing_s`).

### `finish`

The image was sent; the tag did not confirm.
- *Check:* On WOLINK / easyTag this is the **panel refresh** — `finish_s` is how long it waited. On XTE it is the end-command acknowledgement. *device error N* = the tag reported a problem.
- *Do:* Panel: a cold or large panel is slow; usually the image still appears — check the tag. Repeated *device error*: the tag rejected the image (wrong model/packing) — compare the preset with the tag's label.

### Quick checks

- **`rssi` is low but `paths` is 2 or more** — another radio might do better; HA picks the strongest advertisement to connect through, so the alternative is only used after a failure. Check `via` to see which one was used.
- **Everything fails at `connect` right after adding a proxy** — the proxy must be `active: true` in both `esp32_ble_tracker` and `bluetooth_proxy` (see the [README](../README.md#installation)); a passive proxy sees tags but cannot connect.
- **`start_probes` above 1 on successful writes** (PickSmart) — the tag was slow to answer after connecting. Harmless once in a while, but it is where a marginal link shows first; if it is 2–3 on most writes, treat it like a `transfer` problem.
- **Only large images fail** — WOLINK / easyTag panels take longer to refresh the bigger they are; `finish_s` of tens of seconds is normal for 7.5" and above, and the wait allowed grows with the image size. On XTE, `chunk_size: 20` makes a 4.2" image take far longer than 244 would; a different proxy or a local adapter usually reports 244.

## What the attributes cannot show

Three kinds of problem never reach the failure sensors, because the write did not fail — or never happened.

**The write succeeded but the panel shows something else.** `success: true`, and yet the label is unchanged, striped or mirrored. The image reached the tag; the tag decoded it with the wrong geometry or color order — a preset that does not match the hardware. This is where the untested WOLINK / easyTag presets and the size-only XTE presets can be wrong. Compare **Last Updated Content** (what was sent) with a photo of the tag, and check the preset in the diagnostics against the label printed on the tag ([models.md](models.md)). Please [open an issue](https://github.com/eigger/hass-ble-esl/issues) with both — that is how presets get fixed.

**The action itself errored before any BLE traffic.** A template that does not render, a font file that does not exist, a `dlimg` URL that cannot be fetched: the action fails immediately with that message, and nothing is recorded on the write sensors. Reproduce with `dry_run: true` from **Developer tools → Actions** and look at **Preview Content** — if the preview is right, the payload is fine.

**No write was attempted.** The action can end as `locked` (the **Write Lock** switch is on — this stops `ble_esl.write` too) or, with `ble_esl.write_guarded`, as `duplicate` (image unchanged and *Prevent Duplicate Send* is on) or `scheduled` (debounced; it runs later). None of these touch the write sensors. The action's response `status` says which ([actions.md](actions.md#response-data)); for an automation that "does nothing", check its trace first.

## Intermittent failures

A write that fails only sometimes is the reason Last Failure Time keeps its attributes: look there, not at Write Duration, which already shows the later success. Its `failed_stage` and `rssi` at the time of failure are what matter. If failures cluster at one `via`, that proxy is the problem; if `paths` was 1 each time, a second radio would have given a fallback.

Home Assistant also records the Write Duration attributes with each state change, so the history of that sensor around the failure time has the breakdown of every attempt, not only the last failed one.

## What to attach to an issue

1. The **diagnostics download** from the device page. It contains the backend, preset, firmware, options, the last advertisement, `last_write` and `last_failure_write`; the tag's MAC is redacted.
2. For a wrong-looking panel: the **Last Updated Content** image and a photo of the tag.
3. For a failing action: the error message shown by Home Assistant (or the action response with `response_variable`).
4. Which radio the tag uses (`via` — proxy model and ESPHome version, or the adapter) if the failure is `connect` or `transfer`.

Debug logging is rarely needed; if asked, add `custom_components.ble_esl: debug` under `logger:` and reproduce once.
