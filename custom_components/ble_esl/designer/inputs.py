"""Track saved designs' inputs without copying entity lists into automations."""

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import callback
from homeassistant.helpers.template import Template

from .layout import template_variables
from .specs import templates_in

INPUTS_CHANGED = "ble_esl_inputs_changed"


def input_trigger(entry_id):
    """A stable reference, independent of the design's current components."""
    return {
        "trigger": "event",
        "event_type": INPUTS_CHANGED,
        "event_data": {"entry_id": entry_id},
        "id": "ble_esl_inputs",
    }


class DesignInputs:
    """Observe only loaded tags, and refresh dependencies after conditional reads."""

    def __init__(self, designer):
        self.designer = designer
        self.hass = designer.hass
        self.dependencies = {}
        self.unsubscribe = None

    @callback
    def track(self, entry_id):
        entities, domains, all_states = set(), set(), False
        for element in self.designer.documents.get(entry_id, {}).get("elements", []):
            entity_id = element.get("entity_id", "")
            if entity_id:
                entities.add(entity_id)
            variables = template_variables(self.hass.states.get(entity_id), element)
            sources = templates_in(element)
            if template := self.designer.templates.get(element.get("template")):
                sources += templates_in(template)
            for source in dict.fromkeys(sources):
                info = Template(source, self.hass).async_render_to_info(variables)
                # Even a currently failing template records the reads made so far.
                entities.update(info.entities)
                domains.update(info.domains or ())
                domains.update(info.domains_lifecycle or ())
                all_states |= info.all_states
        self.dependencies[entry_id] = entities, domains, all_states
        if self.unsubscribe is None:
            self.unsubscribe = self.hass.bus.async_listen(EVENT_STATE_CHANGED, self.changed)

    @callback
    def untrack(self, entry_id):
        self.dependencies.pop(entry_id, None)
        if not self.dependencies and self.unsubscribe is not None:
            self.unsubscribe()
            self.unsubscribe = None

    @callback
    def changed(self, event):
        entity_id = event.data["entity_id"]
        domain = entity_id.partition(".")[0]
        for entry_id, (entities, domains, all_states) in list(self.dependencies.items()):
            if entity_id not in entities and domain not in domains and not all_states:
                continue
            self.track(entry_id)
            new_state = event.data["new_state"]
            if new_state is None or new_state.state in ("unavailable", "unknown"):
                continue
            self.hass.bus.async_fire(
                INPUTS_CHANGED,
                {"entry_id": entry_id, "entity_id": entity_id},
                context=event.context,
            )
