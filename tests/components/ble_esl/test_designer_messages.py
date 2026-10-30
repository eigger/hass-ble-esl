"""The designer's fixed error messages and the frontend catalog stay in step."""

from pathlib import Path
import re

DESIGNER = Path(__file__).parents[3] / "custom_components" / "ble_esl" / "designer"

# Raised as HomeAssistantError with exactly this text; the frontend translates
# them by looking the text up in its catalog (serverMessage in i18n.js).
FIXED_MESSAGES = [
    "Preview parameters must be a JSON object",
    "Preview parameters must contain finite JSON values",
    "Preview parameters are too large (64 KiB maximum)",
    "This ESL does not support writing",
    "This ESL has no registered device",
    "The automation payload must be a list of objects",
    "The automation payload is too large to import (5 MiB maximum)",
    "That element is not in the display",
    "That is an imagespec element already",
    "Choose a sensor type",
    "Choose an available sample entity",
    "This ESL protocol does not support image writes",
    "The ESL's display size changed; reload the designer",
    "template_id is required",
    "Give the template a name of up to 80 characters",
    "A template id is lowercase letters, digits and underscores",
    "Too many templates share that name",
    "This template has no layout for the display and its polygon cannot be scaled",
    "This is not usable YAML: it is nested too deeply",
    "Paste a payload (a list of elements) or a ble_esl.write action with a payload",
    "Automation is not available",
    "This automation has no editable configuration",
    "Select an automation entity",
    "Select the association to unlink",
    "Automation has no stable ID",
]


def test_fixed_messages_exist_in_the_server_and_the_catalog():
    source = "".join(path.read_text(encoding="utf-8") for path in DESIGNER.glob("*.py"))
    # Adjacent string literals on several lines are one message.
    source = re.sub(r'"\s*\n\s*"', "", source)
    catalog = (DESIGNER / "frontend" / "locales" / "en.js").read_text(encoding="utf-8")
    catalog = re.sub(r'"\s*\n\s*"', "", catalog)
    for message in FIXED_MESSAGES:
        assert message in source, f"no longer raised by the server: {message}"
        assert message in catalog, f"missing from the frontend catalog: {message}"
