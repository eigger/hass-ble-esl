// Hover feedback shared by every stylesheet that styles its own buttons. A
// primary button already has the accent border, so it brightens instead.
// `skip` lists extra selectors (":not(.danger)") whose buttons keep their own
// hover background.
export const primaryHover =
  "button.primary:hover:not(:disabled){filter:brightness(1.18);box-shadow:0 1px 4px #0003}";

export const buttonHover = (skip = "") =>
  `button:not(.primary):hover:not(:disabled){border-color:var(--primary-color,#257d86)}button:not(.primary):not(.swatch):not([aria-pressed="true"]):not([aria-selected="true"]):not(.active)${skip}:hover:not(:disabled){background:color-mix(in srgb,var(--primary-color,#257d86) 10%,var(--card-background-color,white))}`;
