# Troubleshooting

[README](../README.md) | **English** | [한국어](troubleshooting.ko.md)

When a label does not update, the integration has usually already recorded why. Read the diagnostic sensors first, then check the cases they cannot see, and attach the relevant evidence to an issue.

## Common troubleshooting

Start with the [common Bluetooth troubleshooting](https://github.com/eigger/blesession/blob/main/docs/troubleshooting.md). Proxy selection, firmware and Home Assistant registration are covered by the [Bluetooth proxy guide](https://github.com/eigger/blesession/blob/main/docs/bluetooth.md). BLE ESL proxy notes are in [bluetooth.md](bluetooth.md).

## Device-specific checks

The model/firmware hardware results remain those listed in [Supported tags](../README.md#supported-tags); this documentation update did not validate additional tags, local adapters or proxy combinations.

### Discovery vs. connection

A tag that shows up in Home Assistant has only been **discovered**: a radio received its advertisement. That says nothing yet about whether a GATT connection, the protocol handshake or the image transfer will work — those happen only when a write runs. The **Signal Strength** sensor and the advertisement in the diagnostics come from discovery; the write sensors below (`failed_stage`, `via`, the stage timings) come from the connection.

- The radio that heard the tag best is not necessarily the one the connection used. `via` is the radio the link took; when `via_unconfirmed` is `true` it is only the radio that heard the tag best, and `advertised_via` appears when the strongest advertisement came from a different radio than the link.
- Connecting needs `bluetooth_proxy.active: true` on an ESPHome proxy (or a local adapter that can connect); a proxy without it forwards advertisements only. See [bluetooth.md](bluetooth.md#proxy-configuration).
- BLE ESL does not pair or bond with any tag, and no wake-up step (button press or similar) is part of any protocol in this integration. Each write attempt makes up to two connection attempts, because a sleeping tag often answers the second one; whether a particular tag model needs to be woken by hand has **not been verified**.

### Per-protocol conditions

What each protocol does after the link is up, as implemented in [`esl_ble/`](../custom_components/ble_esl/esl_ble/README.md). Where a row says *not verified*, the integration makes no claim either way.

| Protocol | Authentication / pairing | Other apps and integrations | Transfer constraints |
|---|---|---|---|
| **PickSmart** (Gicisky) | No pairing or authentication. After subscribing to notifications the integration waits 0.2 s and sends START up to 3 times (0.4 s each); no answer = `auth` failure with `start_probes: 3`. | Not verified; if a vendor app or another integration is connected to the tag, disconnect it before writing. | 240-byte parts, each acknowledged by the tag; the tag may ask for a part again, and the write gives up after 6 requests in a row for one part. |
| **WOLINK** (Zhsunyco) | No BLE pairing. The tag sends a nonce on its auth characteristic and the integration answers it; a wrong answer makes the tag drop the link and is reported as *device error 5: unlock failed*. | Not verified; disconnect other apps or gateways before writing. | Chunk size follows the negotiated MTU (200–506 bytes, never below 200). The completion wait is the panel refresh and grows with image size. The **Model** option must be picked by hand (WOLINK does not report its model). |
| **easyTag** (Zhsunyco) | No pairing or authentication exchange. Untested on physical tags. | Not verified. | Fixed packet gap (20 ms) and a 20 s reply timeout per frame; the completion wait is the panel refresh. The **Model** option must be picked by hand. |
| **ETAG** (Hipoink) | No pairing. The integration reads the panel firmware after connecting and refuses firmware it does not know without retrying (`SE0213NP61-TNG-A0` verified, `SE0213MN50-TNG-A0` untested). | **Close the companion Bluetooth Label app** before connecting from Home Assistant ([etag.md](etag.md)). | Every 240-byte packet must fit in one write-without-response, so the link needs an ATT MTU of at least 243; less fails with `ETAG write size … is too small`. Each packet is acknowledged; command replies wait up to 30 s. |
| **XTE** (Poshiji) | No pairing or authentication. Presets with an unimplemented pixel layout (some device numbers) are refused **before connecting**. | **Only one integration may write to the tag** ([xte.md](xte.md)). | 0.5 s pause after subscribing to notifications; writes use the smaller of 244 bytes and the link's reported write limit (20 bytes accepted); after a failed attempt the next one writes at most 182 bytes, 30 ms apart. Size-only presets are hand-picked and untested. |

A refused write (unsupported firmware, preset or device number) is not retried: retrying cannot change the answer.

**Power:** a low battery can let the tag keep advertising but drop the link under load (`link_lost`) or fail the panel refresh. Check the **Battery** sensor: it is read from the advertisement on PickSmart, WOLINK and XTE and from the write session on easyTag; ETAG does not report a battery level. The low-battery binary sensor turns on at 2.5 V (10 % on XTE), where e-paper refresh becomes unreliable even though BLE still works ([actions.md](actions.md#entities)).

## Symptoms and actions

| Symptom | Failing stage | Checks | Action |
|---|---|---|---|
| Tag advertises but cannot accept a write | `connect` | Connectable radio, connection slots, `rssi`, `paths` | Enable active proxy connections; move closer or free a slot. |
| Session starts but protocol cannot proceed | `session` / `auth` | Firmware/preset, START reply, WOLINK unlock error | Close vendor apps and compare the protocol/model before retrying. |
| Connection drops or a write never returns | `transfer` / `write_timeout` | Battery under load, `via`, `chunk_size`, error text | Move the tag/proxy; restart a repeatedly unresponsive proxy. |
| Image sent but no completion confirmation | `finish` | Panel temperature/size, `finish_s`, device error | Inspect the physical panel and confirm its preset. |

### Reading a failure

Start with `failed_stage` on Last Failure Time: it says how far the attempt got. `likely_cause` is a one-sentence reading of the stage, the error text and the radio situation; `error` is the exact message.

#### `unreachable`

No radio currently sees the tag's advertisement; nothing was tried.
- *Check:* `error` says *No connectable radio sees …*. Is the proxy/adapter itself up in HA?
- *Do:* Move closer, replace the battery (see the **Battery** sensor), check the proxy is online.

#### `connect`

The link never came up (the tag advertised but did not accept a connection).
- *Check:* `rssi` and `paths` (how many radios reach the tag). `error` with *slot* = the proxy's connection slots are all in use.
- *Do:* Weak `rssi` (below about −85 dBm): move the tag or add a proxy near it — with `paths: 1` there is also no other radio to fall back to. *slot*: fewer BLE devices per proxy, or another proxy. Otherwise usually transient — the retries cover it.

#### `session`

Connected, but the tag dropped or refused the session before the protocol started.
- *Check:* Does it repeat every time?
- *Do:* Once: ignore. Every time: the protocol or model may not match — check the preset in the diagnostics and the model table in [models.md](models.md).

#### `auth` (`failed_detail: handshake`)

The tag did not answer, or answered wrongly, before any image data was sent. `auth` is the shared name for this stage across BLE integrations; `failed_detail` gives the tag's own name for it.
- *Check:* PickSmart `start_probes: 3` = it never answered START. WOLINK *device error 5* = authentication refused. *No response … after command 0x01* (XTE) = no reply to the size command.
- *Do:* Unanswered: the tag was not ready yet — transient, retries cover it; if constant, the tag firmware is not one this protocol knows. Auth refused: not a WOLINK tag, or different firmware. Wrong answer: wrong protocol/model.

#### `transfer`

Failed while sending the image data. This is the one case that points at link quality.
- *Check:* `resends` / `round_trip_ms` (PickSmart), `sends` vs `parts` (how far it got), `chunk_size` (XTE / WOLINK: negotiated chunk size; small values mean tiny writes), `rssi`, `via` (which radio).
- *Do:* Move the tag or the proxy it actually used (`via`), or add one. The next retry is automatically paced slower (`pacing_s`).

#### `finish`

The image was sent; the tag did not confirm.
- *Check:* On WOLINK / easyTag this is the **panel refresh** — `finish_s` is how long it waited. On XTE it is the end-command acknowledgement. *device error N* = the tag reported a problem.
- *Do:* Panel: a cold or large panel is slow; usually the image still appears — check the tag. Repeated *device error*: the tag rejected the image (wrong model/packing) — compare the preset with the tag's label.

#### Quick checks

- **`error: Attempt timed out after 600s …`** (`timed_out: true`) — the attempt hung (usually a proxy that died mid-write while the connection was still being set up or a write was not individually bounded) and was cut at the 10-minute bound. `failed_stage` says where. It is **not retried** — the transport is dead, and the next automation run is the real retry — so a dead proxy costs one bound, not one per retry. Other tags wait at most for that one attempt: the BLE lock covers one attempt, and a tag that is retrying lets the others go first.

- **`error` starts with *The link dropped …*** (`likely_cause_key: link_lost`) — the tag went away mid-session: out of range, the battery gave out under load, or the proxy/adapter reset. The wait ends the moment the link goes rather than running the step's timeout out, so `transfer_s` / `finish_s` show when it happened and the retry starts straight away. Once in a while is normal at the edge of range; repeatedly means `rssi` and `via` — move the tag or the proxy.

- **`likely_cause_key: write_timeout`** — a write to the tag never returned, so the adapter or proxy stopped taking data (the image chunks of WOLINK and XTE are bounded at 10 seconds each, PICKSMART commands at 10 seconds and ETAG commands at 30 seconds; such a write fails and is retried instead of waiting for the 10-minute bound): usually a wedged adapter or a proxy that is busy or has died, not a silent tag. Restart the adapter or proxy if it repeats. Unlike *The link dropped …*, the link had not been reported lost.

- **`likely_cause_key: session.gatt_mismatch`** — the tag connected but does not expose the service or characteristic the protocol needs (or its write size is too small): another model or firmware than the preset assumes, or a link that has not negotiated its MTU. A missing service or characteristic is **not retried**; a too-small write size is, because it can be a link that has not yet negotiated its MTU.

- **`rssi` is low but `paths` is 2 or more** — another radio might do better; HA picks the strongest advertisement to connect through, so the alternative is only used after a failure. Check `via` to see which one was used (if `via_unconfirmed` is `true`, it is only the one that heard the tag best).
- **Everything fails at `connect` right after adding a proxy** — the proxy must have `bluetooth_proxy: active: true` to make connections, and BLE ESL's starting configuration also sets `esp32_ble_tracker: scan_parameters: active: true` (see [bluetooth.md](bluetooth.md#proxy-configuration)); a proxy without `bluetooth_proxy.active` forwards advertisements, so it sees tags but cannot connect.
- **`start_probes` above 1 on successful writes** (PickSmart) — the tag was slow to answer after connecting. Harmless once in a while, but it is where a marginal link shows first; if it is 2–3 on most writes, treat it like a `transfer` problem.
- **Only large images fail** — WOLINK / easyTag panels take longer to refresh the bigger they are; `finish_s` of tens of seconds is normal for 7.5" and above, and the wait allowed grows with the image size. On XTE and WOLINK, a smaller `chunk_size` (e.g. 20 on some XTE proxies, or 200 on low-MTU links) makes large images take far longer than with a higher negotiated MTU; a different proxy or a local adapter usually reports a higher value.

### What the attributes cannot show

Three kinds of problem never reach the failure sensors, because the write did not fail — or never happened.

**The write succeeded but the panel shows something else.** `success: true`, and yet the label is unchanged, striped or mirrored. The image reached the tag; the tag decoded it with the wrong geometry or color order — a preset that does not match the hardware. This is where the untested WOLINK / easyTag presets and the size-only XTE presets can be wrong. Compare **Last Updated Content** (what was sent) with a photo of the tag, and check the preset in the diagnostics against the label printed on the tag ([models.md](models.md)). Please [open an issue](https://github.com/eigger/hass-ble-esl/issues) with both — that is how presets get fixed.

On a **Gicisky 7.5-inch BWR** tag, red stripes or persistent red noise despite a successful write may instead come from a corrupted USB storage volume. The issue reporter fixed this by reformatting the tag's 2 MB USB volume as FAT12; see [issue #177](https://github.com/eigger/hass-ble-esl/issues/177) for the procedure.

**The action itself errored before any BLE traffic.** A template that does not render, a font file that does not exist, a `dlimg` URL that cannot be fetched: the action fails immediately with that message, and nothing is recorded on the write sensors. Reproduce with `dry_run: true` from **Developer tools → Actions** and look at **Preview Content** — if the preview is right, the payload is fine.

**No write was attempted.** The action can end as `locked` (the **Write Lock** switch is on — this stops `ble_esl.write` too) or, with `ble_esl.write_guarded`, as `duplicate` (image unchanged and *Prevent Duplicate Send* is on) or `scheduled` (debounced; it runs later). None of these count as a failure: Failure Count and Last Failure Time are untouched. The action's response `status` says which ([actions.md](actions.md#response-data)); for an automation that "does nothing", check its trace first. A write that reached the BLE lock before being stopped leaves `success: false` with `skipped: locked` / `duplicate` / `dropped` on the **Write Duration** attributes — that is where to look when an automation's trace says the action ran but the tag did not change. This covers every `ble_esl.write` the Write Lock switch blocks (it does not check before queueing) and a guarded write whose conditions changed while it waited its turn; `ble_esl.write_guarded` checks before queueing as well, so an ordinary duplicate returns without recording anything.

### Intermittent failures

A write that fails only sometimes is the reason Last Failure Time keeps its attributes: look there, not at Write Duration, which already shows the later success. Its `failed_stage` and `rssi` at the time of failure are what matter. If failures cluster at one `via`, that proxy is the problem; if `paths` was 1 each time, a second radio would have given a fallback.

Home Assistant also records the Write Duration attributes with each state change, so the history of that sensor around the failure time has the breakdown of every attempt, not only the last failed one.

### `Missing required argument(s) 'y'` in the automation editor

Home Assistant's YAML editor reads YAML 1.1, where a bare `y` (also `n`, `yes`, `no`, `on`, `off`) is a boolean. Saving `y: 22` turns the key into `'true': 22`, and a colour written as `color: y` becomes `true`. Write them quoted: `"y": 22` and `color: "y"`. The integration repairs a `true` key back to `y` and logs a warning, but quoting is the real fix. YAML exported by the designer is already quoted.

## Diagnostics and logs

### Where to look

Open the tag's device page (**Settings → Devices & services → BLE ESL → the tag**). Under *Diagnostic* there are three entities to read, in this order:

| Entity | What it tells you |
|---|---|
| **Last Failure Time** | When the last write **failed** (every retry exhausted). Its *attributes* are the breakdown of that failed write — `failed_stage`, `likely_cause`, `error`, the radio (`via`, `rssi`, `paths`) and the stage timings. They stay until the next failure, so a failure from last night is still readable after this morning's writes succeeded. |
| **Write Duration** | Seconds of the **most recent** write, success or not. Its *attributes* are the same breakdown for that attempt. Use it when the write you are debugging is the last one. |
| **Failure Count** | How many writes have failed since the integration was (re)loaded. Rising while labels look fine means writes are failing inside an automation nobody is watching. |

To see the attributes: click the entity → ⋮ → **Attributes**, or in **Developer tools → States** search for the entity. In a template:

```jinja
{{ state_attr('sensor.<brand>_<id>_last_failure_time', 'likely_cause') }}
```

 — e.g. `sensor.gicisky_a1b2c3d4_…` for a PickSmart tag, `sensor.zhsunyco_a1b2c3d4_…` for WOLINK / easyTag, `sensor.poshiji_a1b2c3d4_…` for XTE (the id is the last 8 hex digits of the MAC).

The same breakdown is in the **diagnostics download** (device page → ⋮ → *Download diagnostics*, `write_state.last_write` and `write_state.last_failure_write`) and, when an automation asks for it, in the action's response (`response_variable` → `timing`).

Two more entities help, but read them for what they are:

- **Display In Sync** (binary) — on when the last image *rendered* matches the last known image the tag *received*; off when they differ, for example when a `dry_run` or failed write rendered a different image. It is `unknown` when either image is unknown, including after a reload during an active write because the tag may finish after the integration reloads. It does not know what the panel physically shows.
- **Connectivity** (binary) — on **while a write is in progress**, from the first attempt to the final result, including connection retries; off otherwise. It is not "the tag is nearby", nor "the link is up".

### Enabling and disabling logs

Enable debug logs only for the reproduction interval:

```yaml
logger:
  default: info
  logs:
    custom_components.ble_esl: debug
    blesession: debug
```

Both logger names are used by the integration and its transport library. Reproduce once, save the relevant log window, then remove these overrides (or set them to `info`) and reload logging/restart Home Assistant. Review logs and diagnostics for addresses, credentials, tokens and personal data before sharing them.

## If the problem persists

Use the existing [Issues and issue templates](https://github.com/eigger/hass-ble-esl/issues); follow the selected template. Include Home Assistant, BLE ESL, ESPHome and blesession versions when available, device/proxy model and revision, local/proxy connection method, failure time and stage, and reproduction steps. Report successful and failed attempts separately.

### What to attach to an issue

1. The **diagnostics download** from the device page. It contains the protocol, preset, firmware, options, the last advertisement, `last_write` and `last_failure_write`; the tag's MAC is redacted.
2. For a wrong-looking panel: the **Last Updated Content** image and a photo of the tag.
3. For a failing action: the error message shown by Home Assistant (or the action response with `response_variable`).
4. Which radio the tag uses (`via` — proxy model and ESPHome version, or the adapter) if the failure is `connect` or `transfer`.

Debug logging is rarely needed; if asked, add `custom_components.ble_esl: debug` under `logger:` and reproduce once.

#### Remove sensitive information before posting

Issues and Discussions are public. The diagnostics download redacts the tag's `address` and `unique_id` and masks the tag's MAC inside the advertised name and source, but it does not remove everything:

- `via` / `advertised_via` (in `last_write`, `last_failure_write`, entity attributes and action responses) contain the **proxy's or adapter's** name and MAC, and the advertisement's `source` in the diagnostics is the receiving radio's address. Replace them with something like `esp-proxy-1 (XX:XX:…)` if you do not want to share them; keep the proxy model and whether it is a proxy or a local adapter.
- The device identifier and entity IDs contain the last 8 hex digits of the tag's MAC. That is enough to tell tags apart; replace it if you prefer.
- Payloads, **Last Updated Content** images, error messages and automation traces can contain your calendar entries, names, addresses, URLs with tokens or other personal data from your entities. Crop or blank them.
- Debug logs: collect only the reproduction window under the `custom_components.ble_esl` logger, check them for addresses and tokens, and turn debug logging off afterwards.
