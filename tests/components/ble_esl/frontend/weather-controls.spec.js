import { expect, test } from "@playwright/test";
import { renderWeatherControls } from "../../../../custom_components/ble_esl/designer/frontend/editor/inspector/weather-controls.js";

const translate = (message) => message;

test("weather inspector offers its time and field options with HA labels", () => {
  const controls = renderWeatherControls(
    { entity_id: "weather.home" },
    { translate },
  );

  expect(controls).toContain(
    '<select data-property="weather_when" aria-label="Weather time">',
  );
  expect(controls).toContain('<option value="now" selected>Now</option>');
  expect(controls).toContain('<option value="in_3_days" >In 3 days</option>');
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

test("weather inspector retains authored time and field selections", () => {
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
  expect(controls).not.toContain('<option value="now" selected>');
  expect(controls).not.toContain('<option value="condition" selected>');
});
