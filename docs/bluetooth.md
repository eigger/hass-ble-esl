# Bluetooth setup

**English** | **[한국어](ko/bluetooth.md)**

BLE ESL connects to each tag over GATT (through `blesession`) to send an image. Home Assistant needs a Bluetooth adapter or an ESPHome Bluetooth proxy that can make **active connections**; seeing a tag's advertisement is not enough to write to it.

The shared proxy setup, recommended hardware and the generic connection troubleshooting order live in the [Bluetooth proxy guide](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/bluetooth.md) (Korean; checked 2026-10-18). This page keeps what is specific to BLE ESL; tag-specific conditions and the failure sensors are in [troubleshooting.md](troubleshooting.md).

## Proxy configuration

Use a **Bluetooth proxy** rather than the host's built-in adapter whenever you can, and set it to **active** — most write problems trace back to a passive proxy or a weak adapter. Keep the scan interval at its default.

The snippet below is only the Bluetooth part of an ESP32 ESPHome configuration, not a complete firmware file; merge it with the board, network and API settings of your own configuration.

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

The two `active` keys do different things:

- `bluetooth_proxy.active: true` lets Home Assistant open **GATT connections** through the proxy. BLE ESL needs this for every write; a proxy without it only forwards advertisements.
- `esp32_ble_tracker.scan_parameters.active: true` is the **scan mode** (it requests scan responses). It is the starting configuration used with BLE ESL; it is not by itself what makes connections possible.

> [!TIP]
> Hardware suggestions: the [Seeed Studio XIAO W5500](https://ko.aliexpress.com/item/1005009310322353.html) (XIAO ESP32 with wired Ethernet) is a good proxy — Ethernet keeps the radio free for BLE, and the community thread [Great ESP32 board for an ESPHome Bluetooth proxy](https://community.home-assistant.io/t/great-esp32-board-for-an-esphome-bluetooth-proxy/916767/31) covers other boards. The shared guide lists the board revision to buy (XIAO W5500 **V1.2**) and a USB-A dongle alternative.

These suggestions do not mean every proxy/tag combination has been tested with BLE ESL. A local adapter that already works reliably does not need to be replaced.

## What is specific to BLE ESL

- **Discovery is not a connection.** A tag that appears in Home Assistant (discovered from its advertisement) has not yet been connected to. The first real GATT connection happens on the first write; see [Discovery vs. connection](troubleshooting.md#discovery-vs-connection).
- **One write at a time.** Writes to all tags share one BLE lock: one attempt holds the radio at a time, and a tag that has to retry lets the others go first.
- **Integration options are not proxy settings.** Retry Count, Prevent Duplicate Send and Debounce Delay are BLE ESL options ([usage.md](usage.md#options)); they do not change the proxy firmware, and they are not defaults for other Bluetooth integrations.
- **Per-protocol conditions** (authentication, minimum write size, companion apps) are listed in [troubleshooting.md](troubleshooting.md#per-protocol-conditions).
