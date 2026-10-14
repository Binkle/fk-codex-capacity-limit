"""Render the Windows installer's vector UI resources at 2x resolution."""

import base64
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_assets(output: Path) -> None:
    application = QGuiApplication.instance() or QGuiApplication([])
    assets = Path(__file__).resolve().parent / "assets"
    output.mkdir(parents=True, exist_ok=True)
    # Keep text in native controls for localization and accessibility. Binding the
    # existing icon into the background avoids grey static-control boxes on MSI.
    for name, source, width, height in (
        ("welcome", "welcome", 640, 386),
        ("sidebar", "sidebar", 164, 314),
        ("header", "header", 150, 57),
        ("msi-welcome", "welcome", 493, 312),
        ("msi-banner", "header", 493, 58),
        ("msi-dialog", "sidebar", 493, 312),
    ):
        canvas = QImage(width * 2, height * 2, QImage.Format.Format_RGB32)
        canvas.fill(0xFFFFFFFF)
        painter = QPainter(canvas)
        painter.scale(2, 2)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        markup = (assets / f"windows-{source}.svg").read_text(encoding="utf-8")
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
