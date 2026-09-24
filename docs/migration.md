# Migrating from hass-gicisky

English | **[한국어](ko/migration.md)**

[`hass-gicisky`](https://github.com/eigger/hass-gicisky) is archived; `hass-ble-esl`
is its successor with the same PickSmart (Gicisky) protocol, payload format, options
and entities. Only the integration **domain** changed (`gicisky` → `ble_esl`), and
Home Assistant cannot move config entries between domains — so tags are re-added
and action names renamed. Nothing in your payload YAML changes.

## Quick version

1. **Remove the old integration** — delete the Gicisky device entries under
   **Settings → Devices & services**, then uninstall `hass-gicisky` (HACS → Remove,
   or delete `custom_components/gicisky`).
2. **Install `hass-ble-esl`** via HACS and restart Home Assistant.
3. **Add the tags** — they are auto-discovered like before; confirm each one.
4. **Update automations** — rename `gicisky.write` → `ble_esl.write`
   (`gicisky.write_guarded` → `ble_esl.write_guarded`) and reselect the target
   device, since the device ID is new. The payload stays as-is.

That is all most setups need. The rest of this page explains each step in detail,
what to note down beforehand, and how to verify the result.

## Detailed version

### What changes at a glance

| | `hass-gicisky` | `hass-ble-esl` |
|---|---|---|
| Domain / folder | `gicisky` · `custom_components/gicisky` | `ble_esl` · `custom_components/ble_esl` |
| Actions (services) | `gicisky.write`, `gicisky.write_guarded` | `ble_esl.write`, `ble_esl.write_guarded` |
| Action parameters | `payload`, `rotate`, `background`, `dry_run`, `debounce_override_ms` | **unchanged** |
| Payload format | imagespec element list | **unchanged** |
| Device name | `Gicisky <last 8 hex of MAC>` | `Gicisky <last 8 hex of MAC>` (same) |
| Entities | Battery, Battery Voltage, Signal Strength, Connectivity, Display In Sync, Write Duration, Failure Count, Last Failure Time, Last Updated Content, Preview Content, Alias, Write Lock | same set; entity registry entries are new (unique IDs are prefixed `ble_esl_` instead of `gicisky_`) |
| Options | Retry Count, Write Delay, Prevent Duplicate Send, Debounce Delay | Retry Count, Prevent Duplicate Send, Debounce Delay — Write Delay is gone (retries pace themselves); a **Model** option appears only for protocols without auto detection, PickSmart tags detect their model from the advertisement |
| Model detection | from advertisement | from advertisement; unknown device numbers fall back to a manual model pick |
| Fonts | `custom_components/gicisky/fonts/`, then `config/www/fonts/` | `custom_components/ble_esl/fonts/`, then `config/www/fonts/` |
| Minimum Home Assistant | 2025.1 | **2025.12** |
| New in `ble_esl` | — | multi-target `target:` (device / area / floor / label), `response_variable` per-tag results, diagnostics download, per-stage write timings |

### Before you start

1. **Home Assistant 2025.12 or newer** is required.
2. Note anything you customised on the old devices — it is not carried over:
   - the **Alias** text entity value,
   - the **Options** (retry count, prevent duplicate send, debounce),
   - renamed entity IDs, custom names, icons, and area assignments on the entities.
3. Find every place that calls the old actions. In **Developer tools → Actions**
   or with a text search over your config, look for `gicisky.write` and
   `gicisky.write_guarded` in automations, scripts, blueprints, Node-RED flows,
   and dashboard buttons.
4. Do the migration in the order below. Both integrations discover the same
   Bluetooth advertisement (manufacturer ID `0x5053`); if both are installed at
   the same time, both will try to claim the tag and the new entities get an
   `_2` suffix.

### Step 1 — Remove the old integration entries

**Settings → Devices & services → Integrations → Gicisky**: open each device
entry and delete it (⋮ → **Delete**), or delete the whole integration.

### Step 2 — Uninstall `hass-gicisky`

- **HACS:** HACS → **Integrations** → *Gicisky* → ⋮ → **Remove**. Then remove
  the custom repository (HACS → ⋮ → **Custom repositories**) so the archived
  repo no longer shows up.
- **Manual install:** delete the folder `custom_components/gicisky`.

Custom fonts you placed in `config/www/fonts/` stay where they are and keep
working. Fonts you copied *into* `custom_components/gicisky/fonts/` are lost
with the folder — move them to `config/www/fonts/` first.

### Step 3 — Install `hass-ble-esl`

1. HACS → **Integrations** → ⋮ → **Custom repositories** →
   `https://github.com/eigger/hass-ble-esl`, category *Integration* → install
   **BLE ESL**. (Or copy `custom_components/ble_esl` from a release manually.)
2. **Restart Home Assistant.**

### Step 4 — Add the tags again

After the restart, PickSmart tags that are advertising show up under
**Settings → Devices & services → Discovered** exactly as they did with
`hass-gicisky`. Confirm each one. You can also add them manually with
**Add integration → BLE ESL**, which lists every unconfigured tag in range.

- The model (size, colours, panel type) is read from the tag's advertisement,
  so there is no model step for a known tag.
- If a tag's device number is not in the catalog yet, the flow asks you to pick
  the model from a list. Choose the entry matching the panel size and colours;
  then please [open an issue](https://github.com/eigger/hass-ble-esl/issues)
  with the diagnostics download so the device number can be added.

The device is again named `Gicisky <identifier>`, where the identifier is the
last 8 hex digits of the MAC address. Because the naming scheme is the same and
the old entities were deleted first, the default entity IDs usually come back
identical (e.g. `image.gicisky_a1b2c3d4_last_updated_content`). Check under the
device page; if you had renamed entity IDs, rename them again.

### Step 5 — Re-apply the options

**Settings → Devices & services → BLE ESL → the device → Configure** and set
Retry Count, Prevent Duplicate Send and Debounce Delay to the values
you noted. Set the **Alias** text entity and the **Write Lock** switch if you
used them.

### Step 6 — Update automations, scripts and dashboards

Change the action name; keep everything else.

```diff
-action: gicisky.write
+action: ble_esl.write
 target:
   device_id: 1234567890abcdef1234567890abcdef
 data:
   payload:
     - type: text
       value: Hello World!
       x: 10
       y: 10
       size: 40
```

```diff
-action: gicisky.write_guarded
+action: ble_esl.write_guarded
 target:
   device_id: 1234567890abcdef1234567890abcdef
 data:
   debounce_override_ms: 0
   payload: ...
```

Also update:

- **`device_id` targets** — the device is re-created, so its ID is new. Reselect
  the device in the automation editor, or switch the target to the area/label
  the tag lives in (`ble_esl` accepts `area_id`, `floor_id`, `label_id`, and
  entity targets, and several tags per call).
- **Entity references** in dashboards, templates and conditions
  (`sensor.gicisky_…_battery`, `binary_sensor.gicisky_…_display_in_sync`,
  `image.gicisky_…_last_updated_content`, …) — usually unchanged, but verify.
- **Blueprints / packages** that hard-code `gicisky.` as the domain.

Everything under `payload:` (elements, fonts, `dlimg` URLs, `plot` entities,
`dither`) works without modification. The [examples](../examples/README.md) and
web tools that were written for Gicisky tags are the same ones this repository ships.

### Step 7 — Verify

1. Call `ble_esl.write` with `dry_run: true` from **Developer tools → Actions**
   and check the **Preview Content** image entity renders as before.
2. Send a real write and confirm **Display In Sync** turns on and
   **Failure Count** stays at 0.
3. If a write fails, look at the **Write Duration** sensor attributes
   (`attempt`, `error`, `start_probes`, `round_trip_ms`) or download
   **⋮ → Download diagnostics** from the device page — it contains the backend,
   preset, firmware, options and the last advertisement, and is what an issue
   report needs.

### Frequently asked

**Do I have to migrate?** `hass-gicisky` keeps working as long as Home Assistant
does not break it, but it is archived and receives no fixes. New tag models,
protocol fixes and features land only in `hass-ble-esl`.

**Can I run both at the same time?** Not usefully: both integrations discover
the same advertisement and will compete for the tag. Remove the old one first.

**Is the image sent any differently?** No. The PickSmart writer, compression and
presets were carried over from `hass-gicisky` and are the only backend verified
on real hardware; see the model table in [models.md](models.md).

**What about history?** Recorder history is keyed by entity ID. When the new
entity gets the same ID as the old one, long-term statistics continue; otherwise
the old history stays under the old ID until it is purged.

### Coming from `hass-zhsunyco`

`hass-zhsunyco` was renamed into this repository; its `zhsunyco` domain went
through the same domain change. The steps above apply with these differences:

- Remove the **Zhsunyco** entries and `custom_components/zhsunyco`; actions become
  `ble_esl.write` / `ble_esl.write_guarded` instead of `zhsunyco.write` /
  `zhsunyco.write_guarded`.
- easyTag tags cannot report their model, so the flow and the **Options**
  dialog have a **Model** picker — choose the same size you had. A WOLINK tag
  whose display version is known skips that step; any other WOLINK tag asks
  once, during setup, and not again in **Options**.
- Devices keep the `Zhsunyco <id>` name, so the default entity IDs usually come
  back identical, as with Gicisky tags.
