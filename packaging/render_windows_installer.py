"""Render the Windows installer's vector UI resources at 2x resolution."""

import base64
import os
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QRawFont
from PySide6.QtSvg import QSvgRenderer


def load_installer_fonts() -> None:
    # Qt's offscreen platform does not enumerate Windows system fonts. Without
    # explicit registration, SVG text silently renders as missing-glyph boxes.
    if os.name == "nt":
        fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for filename in ("segoeui.ttf", "seguisb.ttf"):
            source = fonts / filename
            if QFontDatabase.addApplicationFont(str(source)) < 0:
                raise RuntimeError(f"Cannot load installer font: {source}")


def validate_artwork_text(markup: str) -> None:
    font = QRawFont.fromFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
    for element in ET.fromstring(markup).iter("{http://www.w3.org/2000/svg}text"):
        text = "".join(element.itertext())
        if text and (
            not font.isValid()
            or not font.familyName()
            or 0 in font.glyphIndexesForString(text)
        ):
            raise RuntimeError(f"Installer font cannot render artwork text: {text!r}")


def render_assets(output: Path) -> None:
    application = QGuiApplication.instance() or QGuiApplication([])
    load_installer_fonts()
    assets = Path(__file__).resolve().parent / "assets"
    output.mkdir(parents=True, exist_ok=True)
    # Keep localized text in native controls. Only the fixed brand name is part
    # of the sidebar artwork; validate its glyphs before producing any bitmap.
    for name, source, width, height in (
        ("welcome", "welcome", 640, 386),
        ("sidebar", "sidebar", 164, 314),
        ("header", "header", 150, 57),
        ("msi-welcome", "welcome", 493, 312),
        ("msi-banner", "header", 493, 58),
        ("msi-dialog", "sidebar", 493, 312),
    ):
        markup = (assets / f"windows-{source}.svg").read_text(encoding="utf-8")
        validate_artwork_text(markup)
        canvas = QImage(width * 2, height * 2, QImage.Format.Format_RGB32)
        canvas.fill(0xFFFFFFFF)
        painter = QPainter(canvas)
        painter.scale(2, 2)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        if "APP_ICON_URI" in markup:
            icon = base64.b64encode((assets / "codex-capacity-watcher-icon.png").read_bytes()).decode("ascii")
            markup = markup.replace("APP_ICON_URI", "data:image/png;base64," + icon)
        svg = QSvgRenderer(markup.encode("utf-8"))
        if not svg.isValid():
            raise RuntimeError(f"Invalid installer artwork: {source}")
        if name == "msi-dialog":
            svg.render(painter, QRectF(0, 0, 164, height))
        elif name == "header":
            painter.translate(width - 493, 0)
            svg.render(painter, QRectF(0, 0, 493, height))
        else:
            svg.render(painter, QRectF(0, 0, width, height))
        painter.end()
        target = output / f"{name}.bmp"
        if not canvas.convertToFormat(QImage.Format.Format_RGB888).save(str(target), "BMP"):
            raise RuntimeError(f"Cannot save installer resource: {target}")
    application.processEvents()
    print(f"Rendered Windows installer resources: {output}")


if __name__ == "__main__":
    render_assets(Path(__file__).resolve().parent.parent / "build" / "installer-artwork")
