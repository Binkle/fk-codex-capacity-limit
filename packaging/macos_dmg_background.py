"""Draw the bilingual Finder installation background at 1x and 2x scale."""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen


WINDOW_SIZE = (720, 500)
APP_POSITION = (180, 238)
APPLICATIONS_POSITION = (540, 238)


def _text(painter, y, text, size, color, bold=False):
    font = QFont("Helvetica Neue")
    font.setPixelSize(size)
    font.setBold(bold)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRectF(32, y, 656, 32), Qt.AlignmentFlag.AlignCenter, text)


def render_background(directory: Path) -> Path:
    """Keep text sharp on Retina displays without depending on user fonts."""
    application = QGuiApplication.instance() or QGuiApplication([])
    directory.mkdir(parents=True, exist_ok=True)
    for scale in (1, 2):
        width, height = WINDOW_SIZE
        image = QImage(width * scale, height * scale, QImage.Format.Format_RGB32)
        image.fill(QColor("#f4f7fb"))
        painter = QPainter(image)
        painter.scale(scale, scale)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        _text(painter, 38, "Codex Capacity Watcher", 26, "#172033", True)
        _text(painter, 82, "将左侧应用拖入右侧 Applications 文件夹", 16, "#334155")
        _text(painter, 110, "Drag the app into Applications to install", 14, "#64748b")

        painter.setPen(QPen(QColor("#e3e9f2"), 1))
        painter.setBrush(QColor("#ffffff"))
        for x in (70, 430):
            painter.drawRoundedRect(QRectF(x, 168, 220, 176), 18, 18)

        painter.setPen(QPen(QColor("#2f80ed"), 4, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(QPointF(322, 238), QPointF(398, 238))
        painter.drawLine(QPointF(384, 224), QPointF(398, 238))
        painter.drawLine(QPointF(384, 252), QPointF(398, 238))

        _text(painter, 374, "复制完成后，从“应用程序”打开应用，再推出此磁盘。", 14, "#475569")
        _text(painter, 402, "After copying, open from Applications and eject this disk.", 13, "#64748b")
        painter.end()
        suffix = "@2x" if scale == 2 else ""
        path = directory / f"installer{suffix}.png"
        if not image.save(str(path)):
            raise RuntimeError(f"Cannot save installation background: {path}")
    # Retain the application until all font rendering has finished.
    application.processEvents()
    return directory / "installer.png"
