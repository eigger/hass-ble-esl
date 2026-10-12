// Sensor output and template rules shared by designer workflows.
export function sensorType(state) {
  return `${state.entity_id.split(".")[0]}:${state.attributes.device_class || "default"}`;
}

export function outputType(state) {
  if (!state) return "text";
  if (state.entity_id.startsWith("weather.")) return "weather";
  if (
    state.entity_id.startsWith("binary_sensor.") ||
    ["on", "off"].includes(state.state)
  )
    return "binary";
  return (state.state.trim() !== "" && Number.isFinite(Number(state.state))) ||
    state.attributes.unit_of_measurement
    ? "numeric"
    : "text";
}

export function templateCompatibility(template, key) {
  const type = template?.sensor_type || key;
  if (type.startsWith("output:")) return type.split(":")[1];
  if (type.startsWith("binary_sensor:")) return "binary";
  if (type.startsWith("weather:")) return "weather";
  return "numeric";
}

export function templateTypes(templates, drafts) {
  return [
    ...new Set([
      "output:numeric",
      "output:binary",
      "output:text",
      "output:weather",
      ...Object.keys(templates),
      ...drafts.keys(),
    ]),
  ];
}

export function createDefaultSensorTemplate({ emptyDocument, newElement }) {
  const tag = { width: 140, height: 60, colors: "BWRY" };
  const make = (type, fields) => ({ ...newElement(type, tag), ...fields });
  return {
    ...emptyDocument(),
    elements: [
      make("icon", { x: 4, y: 14, width: 32, height: 32, icon: "{{icon}}" }),
      make("text", {
        x: 44,
        y: 4,
        width: 92,
        height: 18,
        font_size: 12,
        text: "{{name}}",
      }),
      make("text", {
        x: 44,
        y: 25,
        width: 92,
        height: 31,
        font_size: 20,
        text: "{{state}} {{unit}}",
      }),
    ],
  };
}
