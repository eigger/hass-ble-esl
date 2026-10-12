// Prepares the legacy sensor inspector's choices from explicit editor data.
// Home Assistant lookup, localization, and document edits stay at the panel.
const WEATHER_STATES = Object.freeze([
  "sunny",
  "cloudy",
  "partlycloudy",
  "rainy",
  "pouring",
  "snowy",
  "snowy-rainy",
  "clear-night",
  "fog",
  "windy",
  "hail",
  "lightning",
  "lightning-rainy",
]);

export function buildSensorOptions(
  element,
  {
    mode,
    templateKey,
    templates,
    templateDrafts,
    templateSensorType,
    state,
    entities,
    outputType,
    templateCompatibility,
    sensorType,
    outputStyleLabel,
  },
) {
  const options = {
    isWeather: false,
    templateStyles: [],
    templateStates: [],
    numeric: false,
  };

  if (element.type === "sensor") {
    options.isWeather = element.entity_id.startsWith("weather.");
    options.templateStyles = Object.keys(templates)
      .filter(
        (key) =>
          templateCompatibility(templates[key], key) === outputType(state),
      )
      .map((key) => ({
        value: key,
        label:
          templates[key]?.name ||
          templateDrafts.get(key)?.name ||
          (key.startsWith("output:")
            ? outputStyleLabel(key.split(":")[1])
            : key.replace(":", " · ")),
        selected: element.template === key,
      }));
    options.numeric =
      state &&
      !state.entity_id.startsWith("binary_sensor.") &&
      (state.entity_id.startsWith("weather.")
        ? element.weather_field && element.weather_field !== "condition"
        : state.state.trim() !== "" && Number.isFinite(Number(state.state)));
  }

  if (mode === "template" && element.type !== "icon")
    options.templateStates = [
      ...new Set([
        "on",
        "off",
        ...(templateKey.startsWith("weather:") ? WEATHER_STATES : []),
        ...entities
          .filter((entity) => sensorType(entity) === templateSensorType)
          .map((entity) => entity.state),
      ]),
    ];

  return options;
}
