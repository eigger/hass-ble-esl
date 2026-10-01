# Minew MTag15 discovery

The Minew MTag15 1.54-inch 200 × 200 black/white/red/yellow tag is recognized by company ID `0x0639` and CA identification/status frames. Discovery and connection were observed on physical tags; this PR exposes discovery and advertised battery percentage in Home Assistant.

CA00 identification frames contain the tag ID, battery percentage, firmware version and screen ID. Screen ID 65 maps to the MTag15 preset. CA21 status frames identify the protocol but carry no tag ID or model metadata. Unknown screen IDs are not auto-assigned to this preset.

**Image writes are not supported.** Authentication and image transfer have not been verified. Write attempts fail explicitly with `WriteRefused`; palette conversion is available for local previews only. This PR does not implement wake broadcasts, gateway authentication or cloud credentials.
