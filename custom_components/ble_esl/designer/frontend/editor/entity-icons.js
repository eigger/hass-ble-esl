/** Return the same default icon used by the designer for a Home Assistant entity. */
export function defaultEntityIcon(state) {
  if (!state) return "mdi:eye";
  if (state.attributes.icon) return state.attributes.icon;
  const active = state.state === "on",
    deviceClass = state.attributes.device_class;
  if (state.entity_id.startsWith("weather."))
    return (
      "mdi:" +
      ({
        sunny: "weather-sunny",
        "clear-night": "weather-night",
        partlycloudy: "weather-partly-cloudy",
        cloudy: "weather-cloudy",
        rainy: "weather-rainy",
        pouring: "weather-pouring",
        snowy: "weather-snowy",
        "snowy-rainy": "weather-snowy-rainy",
        fog: "weather-fog",
        windy: "weather-windy",
        "windy-variant": "weather-windy-variant",
        lightning: "weather-lightning",
        "lightning-rainy": "weather-lightning-rainy",
        hail: "weather-hail",
        exceptional: "alert-circle",
      }[state.state] || "weather-cloudy")
    );
  if (state.entity_id.startsWith("binary_sensor.")) {
    const pairs = {
      window: ["window-closed", "window-open"],
      door: ["door-closed", "door-open"],
      motion: ["motion-sensor-off", "motion-sensor"],
      plug: ["power-plug-off", "power-plug"],
      power: ["flash-off", "flash"],
      lock: ["lock", "lock-open"],
    };
    return (
      "mdi:" +
      (pairs[deviceClass] || ["radiobox-blank", "checkbox-marked-circle"])[
        Number(active)
      ]
    );
  }
  return (
    "mdi:" +
    ({
      temperature: "thermometer",
      humidity: "water-percent",
      battery: "battery",
      power: "flash",
      energy: "lightning-bolt",
      timestamp: "calendar-clock",
    }[deviceClass] || "eye")
  );
}
