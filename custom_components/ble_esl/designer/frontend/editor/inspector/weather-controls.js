const weatherTimes = [
  ["now", "Now"],
  ["later_today", "Later today"],
  ["tomorrow", "Tomorrow"],
  ["in_2_days", "In 2 days"],
  ["in_3_days", "In 3 days"],
];

const weatherFields = [
  ["condition", "Condition"],
  ["temperature", "Temperature"],
  ["templow", "Low temperature"],
  ["precipitation", "Rain / snow"],
  ["precipitation_probability", "Rain chance"],
  ["wind_speed", "Wind speed"],
  ["humidity", "Humidity"],
];

export function renderWeatherControls(element, { translate }) {
  const timeOptions = weatherTimes
    .map(
      ([value, label]) =>
        `<option value="${value}" ${(element.weather_when || "now") === value ? "selected" : ""}>${translate(label)}</option>`,
    )
    .join("");
  const fieldOptions = weatherFields
    .map(
      ([value, label]) =>
        `<option value="${value}" ${(element.weather_field || "condition") === value ? "selected" : ""}>${translate(label)}</option>`,
    )
    .join("");

  return `<label>${translate("When")}<select data-property="weather_when" aria-label="${translate("Weather time")}">${timeOptions}</select></label><label>${translate("Show")}<select data-property="weather_field" aria-label="${translate("Weather value")}">${fieldOptions}</select></label>`;
}
