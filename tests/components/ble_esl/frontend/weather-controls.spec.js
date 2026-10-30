import { expect, test } from "@playwright/test";
import { renderWeatherControls } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/weather-controls.js";

const translate = (message) => message;

test("weather inspector offers its field options with HA labels and no forecast time", () => {
  const controls = renderWeatherControls(
    { entity_id: "weather.home" },
    { translate },
  );

  expect(controls).not.toContain("weather_when");
  expect(controls).toContain(
    '<select data-property="weather_field" aria-label="Weather value">',
  );
  expect(controls).toContain(
    '<option value="condition" selected>Condition</option>',
  );
  expect(controls).toContain(
    '<option value="precipitation_probability" >Rain chance</option>',
  );
  expect(controls).toContain('<option value="humidity" >Humidity</option>');
});

test("weather inspector keeps the time of an older design so it can be set back to now", () => {
  const controls = renderWeatherControls(
    {
      weather_when: "tomorrow",
      weather_field: "wind_speed",
    },
    { translate },
  );

  expect(controls).toContain(
    '<option value="tomorrow" selected>Tomorrow</option>',
  );
  expect(controls).toContain(
    '<option value="wind_speed" selected>Wind speed</option>',
  );
  expect(controls).toContain('<option value="now" >Now</option>');
  expect(controls).not.toContain('<option value="now" selected>');
  expect(controls).not.toContain('<option value="condition" selected>');
});
