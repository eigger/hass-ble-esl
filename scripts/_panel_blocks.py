"""Building blocks shared by the redesigned smart-home panel layouts.

The generators mix `PanelBlocks` into their own `Canvas` (which provides `text_fit`, `icon`,
`line`, `rect` and the `sx`/`sy`/`scale` factors). All coordinates are in the virtual canvas.
"""


class PanelBlocks:
    """Header bar with a status pill, plus divider-based stat cells."""

    def ms(self, value: float) -> int:
        """A scaled minimum text size."""
        return max(7, round(value * self.scale))

    @property
    def vw(self) -> float:
        return self.width / self.sx

    @property
    def vh(self) -> float:
        return self.height / self.sy

    def header(
        self,
        icon: str,
        title: str,
        badge: tuple[str, str, str, str],
        *,
        bar: float = 44,
        margin: float = 12,
        pill_w: float = 116,
        pill_h: float = 30,
        size: float = 20,
        pill_size: float = 17,
        icon_size: float = 24,
    ) -> None:
        """Black bar: white icon and title on the left, status pill (text, fill, outline, ink)."""
        text, fill, outline, ink = badge
        vw = self.vw
        self.rect(0, 0, vw, bar, fill="black", outline="black")
        self.icon(icon, margin + icon_size / 2, bar / 2, icon_size, color="white")
        left = margin + icon_size + 8
        pill_x = vw - margin - pill_w
        self.text_fit(
            title,
            left,
            4,
            pill_x - left - 8,
            bar - 8,
            size,
            color="white",
            min_size=self.ms(size * 0.7),
        )
        top = (bar - pill_h) / 2
        self.rect(
            pill_x,
            top,
            vw - margin,
            top + pill_h,
            fill=fill,
            outline=outline,
            radius=pill_h / 2,
        )
        self.text_fit(
            text,
            pill_x + 6,
            top + 2,
            pill_w - 12,
            pill_h - 4,
            pill_size,
            align="center",
            color=ink,
            min_size=self.ms(pill_size * 0.8),
        )

    def stat_cells(
        self,
        items: list[tuple[str, str, str, str]],
        top: float,
        bottom: float,
        *,
        x0: float = 12,
        x1: float | None = None,
        label: float = 17,
        value: float = 34,
        icon_size: float = 22,
    ) -> None:
        """Equal columns split by vertical lines: icon + label above, big value below.

        Each item is (icon, label, value template, value colour).
        """
        x1 = self.vw - 12 if x1 is None else x1
        width = (x1 - x0) / len(items)
        label_h = label * 1.45
        for index, (icon, caption, val, color) in enumerate(items):
            x = x0 + index * width
            if index:
                self.line(x, top + 4, x, bottom)
            self.icon(icon, x + 10 + icon_size / 2, top + 4 + label_h / 2, icon_size)
            self.text_fit(
                caption,
                x + 18 + icon_size,
                top + 4,
                width - 26 - icon_size,
                label_h,
                label,
                min_size=self.ms(label * 0.8),
            )
            self.text_fit(
                val,
                x + 10,
                top + label_h + 8,
                width - 20,
                bottom - top - label_h - 10,
                value,
                color=color,
                min_size=self.ms(value * 0.5),
            )
