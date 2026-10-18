# Troubleshooting

[README](../README.md) | **English** | [한국어](troubleshooting.ko.md)

## Common troubleshooting

Start with the [common Bluetooth troubleshooting](https://github.com/eigger/blesession/blob/main/docs/troubleshooting.md). For proxy selection, firmware and Home Assistant registration, use the [Bluetooth proxy guide](https://github.com/eigger/blesession/blob/main/docs/bluetooth.md). For BLE ESL-specific proxy notes, see [bluetooth.md](bluetooth.md).

## Device-specific checks

### Discovery vs. connection

A tag that shows up in Home Assistant has only been **discovered**: a radio received its advertisement. That says nothing yet about whether a GATT connection, the protocol handshake or the image transfer will work — those happen only when a write runs. The **Signal Strength** sensor and the advertisement in the diagnostics come from discovery; the write sensors (`failed_stage`, `via`, the stage timings) come from the connection.

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
| **XTE** (Poshiji) | No pairing or authentication. Presets with an unimplemented pixel layout (some device numbers) are refused **before connecting**. | **Only one integration may write to the tag** ([xte.md](xte.md)). | 0.5 s pause after subscribing to notifications; writes use the smaller of 244 bytes and the link's reported write limit (20 bytes accepted). Size-only presets are hand-picked and untested. |

A refused write (unsupported firmware, preset or device number) is not retried: retrying cannot change the answer.

**Power:** a low battery can let the tag keep advertising but drop the link under load (`link_lost`) or fail the panel refresh. Check the **Battery** sensor: it is read from the advertisement on PickSmart, WOLINK and XTE and from the write session on easyTag; ETAG does not report a battery level. The low-battery binary sensor turns on at 2.5 V (10 % on XTE), where e-paper refresh becomes unreliable even though BLE still works ([actions.md](actions.md#entities)).

## Symptoms and actions

| Symptom | Failing stage | Checks | Action |
|---|---|---|---|
| Tag never discovered | `unreachable` | Radio reception, proxy online state, battery level | Move closer, replace battery, verify proxy has `bluetooth_proxy.active: true` |
| Connection fails repeatedly | `connect` | Weak RSSI (below -85 dBm), proxy connection slots exhausted | Add proxy near tag or reduce BLE devices per proxy |
| Session dropped before protocol start | `session` | Protocol or model mismatch in configuration | Verify preset and model in diagnostics against physical label |
| Handshake / auth fails | `auth` | Tag not ready or unverified firmware | Retries handle transient readiness; verify firmware support for protocol |
| Image transfer interrupted | `transfer` | RF link quality, packet drops, weak RSSI | Check `via` radio, move tag or proxy closer; next retry auto-paces slower |
| Panel refresh unconfirmed | `finish` | Large panel refresh time (tens of seconds for 7.5"+), low battery | Check physical tag display; large/cold panels need more refresh time |
| Automation runs but tag unchanged | `skipped` | Write Lock switch is ON, or duplicate image skipped | Turn off Write Lock switch or disable Prevent Duplicate Send |

### Detailed stage breakdown

- **`unreachable`**: No radio currently sees the tag's advertisement; nothing was tried. Check if the proxy or adapter is online in Home Assistant. Move closer or replace battery.
- **`connect`**: The link never came up (tag advertised but did not accept a connection). Check RSSI and `paths`. If error mentions `slot`, proxy connection slots are exhausted.
- **`session`**: Connected, but tag dropped or refused the session before protocol started. If repeated, check preset in diagnostics and model table in [models.md](models.md).
- **`auth` (`failed_detail: handshake`)**: The tag did not answer, or answered wrongly, before image data was sent. PickSmart `start_probes: 3` = no answer to START; WOLINK *device error 5* = authentication refused.
- **`transfer`**: Failed while sending image data. Check `resends` / `round_trip_ms`, `rssi`, and `via`. Move tag closer or add a proxy.
- **`finish`**: Image was sent but tag did not confirm. On WOLINK / easyTag this is panel refresh (`finish_s`). On XTE it is the end-command acknowledgement.
- **`error: Attempt timed out after 600s …`** (`timed_out: true`): The attempt hung (usually a proxy that died mid-write) and was bounded at 10 minutes. Not retried to avoid locking the queue.
- **`likely_cause_key: link_lost`**: Link dropped mid-session (out of range, battery dip, or proxy reboot). Retry starts immediately.
- **`likely_cause_key: write_timeout`**: A chunk write never returned (bounded at 10 s for chunks, 30 s for ETAG). Usually a wedged adapter or busy proxy; restart the adapter or proxy.
- **`likely_cause_key: session.gatt_mismatch`**: Tag connected but does not expose required service or characteristic, or write size is too small.

## Diagnostics and logs

### Sensor diagnostics

Open the tag's device page (**Settings → Devices & services → BLE ESL → the tag**). Under *Diagnostic* there are three key entities:

- **Last Failure Time**: When the last write failed. Attributes show `failed_stage`, `likely_cause`, `error`, radio (`via`, `rssi`, `paths`), and stage timings.
- **Write Duration**: Seconds of the most recent write (success or failure) with the same attribute breakdown.
- **Failure Count**: How many writes have failed since integration reload.
- **Display In Sync** (binary): `on` when last rendered image matches last received image; `off` when differing; `unknown` if unknown.
- **Connectivity** (binary): `on` while a write is in progress (including retries); `off` otherwise.

The same breakdown is in the **diagnostics download** (device page → ⋮ → *Download diagnostics*, `write_state.last_write` and `write_state.last_failure_write`).

### Debug logging

To collect diagnostic logs, add the following to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.ble_esl: debug
```

Reproduce one write attempt, then remove debug logging.

### Removing sensitive information

Issues and Discussions are public. When sharing diagnostics or logs:
- `via` / `advertised_via` contain proxy/adapter names and MAC addresses. Redact them to e.g. `esp-proxy-1 (XX:XX:…)`.
- Entity IDs contain the tag's MAC identifier (last 8 hex digits).
- Rendered payloads or **Last Updated Content** images may contain personal calendar data, names, or addresses. Crop or blank them.
- Debug logs: inspect for tokens or private addresses before posting.

## If the problem persists

Use this integration's [existing Issues](https://github.com/eigger/hass-ble-esl/issues). When reporting:

1. Attach the **diagnostics download** from the tag's device page.
2. For panel display issues, attach **Last Updated Content** and a physical photo of the tag.
3. For action errors, include the error message or automation trace.
4. Note which radio and proxy model was used (`via`).
