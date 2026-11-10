from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPixmap, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF

def get_app_logo(app_name: str, size: int = 36) -> QPixmap:
    """
    Génère un logo vectoriel ultra-net et fidèle pour les applications de messagerie et système :
    WhatsApp, Discord, Telegram, Chrome, Outlook, Antigravity, etc.
    """
    pix = QPixmap(size * 2, size * 2)  # Retina 2x supersampling
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    name = (app_name or "").lower()
    s = float(size * 2)

    if "whatsapp" in name:
        # 1. WhatsApp : Bulle verte avec combiné téléphonique blanc
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#25D366")))
        p.drawRoundedRect(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9), s * 0.28, s * 0.28)

        # Bulle de dialogue blanche
        bubble_path = QPainterPath()
        bubble_rect = QRectF(s * 0.18, s * 0.18, s * 0.64, s * 0.64)
        bubble_path.addEllipse(bubble_rect)
        # Petite queue de bulle en bas à gauche
        bubble_path.moveTo(s * 0.32, s * 0.72)
        bubble_path.lineTo(s * 0.20, s * 0.82)
        bubble_path.lineTo(s * 0.38, s * 0.78)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawPath(bubble_path)

        # Combiné vert au centre
        p.setPen(QPen(QColor("#25D366"), s * 0.08, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        phone = QPainterPath()
        phone.moveTo(s * 0.38, s * 0.40)
        phone.quadTo(s * 0.42, s * 0.58, s * 0.60, s * 0.62)
        p.drawPath(phone)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#25D366")))
        p.drawEllipse(QPointF(s * 0.38, s * 0.40), s * 0.06, s * 0.06)
        p.drawEllipse(QPointF(s * 0.60, s * 0.62), s * 0.06, s * 0.06)

    elif "discord" in name:
        # 2. Discord : Clyde controller sur fond Blurple #5865F2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#5865F2")))
        p.drawRoundedRect(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9), s * 0.28, s * 0.28)

        p.setBrush(QBrush(QColor(255, 255, 255)))
        # Forme de la tête de Clyde
        clyde = QPainterPath()
        clyde.moveTo(s * 0.25, s * 0.35)
        clyde.quadTo(s * 0.5, s * 0.42, s * 0.75, s * 0.35)
        clyde.quadTo(s * 0.82, s * 0.65, s * 0.68, s * 0.72)
        clyde.lineTo(s * 0.62, s * 0.65)
        clyde.quadTo(s * 0.5, s * 0.68, s * 0.38, s * 0.65)
        clyde.lineTo(s * 0.32, s * 0.72)
        clyde.quadTo(s * 0.18, s * 0.65, s * 0.25, s * 0.35)
        p.drawPath(clyde)

        # Yeux de Clyde en Blurple
        p.setBrush(QBrush(QColor("#5865F2")))
        p.drawEllipse(QPointF(s * 0.39, s * 0.52), s * 0.06, s * 0.08)
        p.drawEllipse(QPointF(s * 0.61, s * 0.52), s * 0.06, s * 0.08)

    elif "telegram" in name:
        # 3. Telegram : Cercle bleu ciel avec avion en papier
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#229ED9")))
        p.drawEllipse(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9))

        # Avion en papier blanc
        p.setBrush(QBrush(QColor(255, 255, 255)))
        plane = QPainterPath()
        plane.moveTo(s * 0.22, s * 0.50)
        plane.lineTo(s * 0.78, s * 0.26)
        plane.lineTo(s * 0.64, s * 0.76)
        plane.lineTo(s * 0.48, s * 0.60)
        plane.lineTo(s * 0.22, s * 0.50)
        p.drawPath(plane)

        # Aile intérieure ombrée
        p.setBrush(QBrush(QColor(215, 235, 250)))
        wing = QPainterPath()
        wing.moveTo(s * 0.48, s * 0.60)
        wing.lineTo(s * 0.55, s * 0.72)
        wing.lineTo(s * 0.58, s * 0.64)
        p.drawPath(wing)

    elif "chrome" in name:
        # 4. Google Chrome : 4 couleurs emblématiques
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#EA4335")))  # Rouge
        p.drawPie(QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84), 30 * 16, 120 * 16)
        p.setBrush(QBrush(QColor("#FBBC05")))  # Jaune
        p.drawPie(QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84), 150 * 16, 120 * 16)
        p.setBrush(QBrush(QColor("#34A853")))  # Vert
        p.drawPie(QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84), 270 * 16, 120 * 16)

        # Cercle blanc séparateur
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.22, s * 0.22)
        # Centre bleu
        p.setBrush(QBrush(QColor("#4285F4")))
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.17, s * 0.17)

    elif "antigravity" in name:
        # 5. Antigravity : Squircle noir avec noyau cyan et anneau orbital
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0a0f1d")))
        p.drawRoundedRect(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9), s * 0.28, s * 0.28)

        # Orbe central cyan
        p.setBrush(QBrush(QColor("#38bdf8")))
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.16, s * 0.16)

        # Anneau elliptique incliné
        p.setPen(QPen(QColor(56, 189, 248, 180), s * 0.04))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(s * 0.5, s * 0.5)
        p.rotate(-35)
        p.drawEllipse(QRectF(-s * 0.35, -s * 0.14, s * 0.70, s * 0.28))
        p.restore()

    else:
        # 6. Fallback par défaut : Squircle moderne avec lettre initiale
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#1e293b")))
        p.drawRoundedRect(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9), s * 0.28, s * 0.28)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.5))
        p.drawRoundedRect(QRectF(s * 0.05, s * 0.05, s * 0.9, s * 0.9), s * 0.28, s * 0.28)

        p.setPen(QColor(255, 255, 255, 230))
        font = QFont("Segoe UI", int(s * 0.42), QFont.Weight.Bold)
        p.setFont(font)
        letter = (app_name[:1] if app_name else "N").upper()
        p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, letter)

    p.end()
    # Retourne en résolution cible
    return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
