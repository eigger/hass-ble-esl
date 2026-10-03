# Hipoink / ETAG

ETAG tags are made by Guangdong SID Technology (brand Hipoink) and used with its Android Bluetooth Label app (`com.gdsid.tag`). Resellers often list them unbranded as "BT ESL". They advertise as `ETAG-<ID>` and use the FFE0/FFE1 GATT service. The supported preset is a 2.13-inch 250 × 122 black/white/red panel.

Discovery, image transfer, per-packet acknowledgments and refresh were verified on a physical tag. Firmware `SE0213NP61-TNG-A0` was verified; the `SE0213MN50-TNG-A0` orientation is derived from the companion app and has not been tested on hardware. Other panel firmware is refused without retrying.

The encoder uses separate black and red bitplanes with column padding, 230-byte image chunks and the app's publish command sequence. A rejected command, unexpected reply, incorrect packet index, notification timeout or dropped link aborts the transfer and is reported through the shared write-failure sensors.

Every 240-byte packet must fit in one write-without-response, so the link needs an ATT MTU of at least 243. A Bluetooth adapter or proxy that negotiates less fails with `ETAG write size … is too small`; please report it if you see that.

Add the tag through the normal BLE ESL flow and use `ble_esl.write`. Close the companion app before connecting from Home Assistant.
