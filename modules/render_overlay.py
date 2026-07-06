import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import argparse
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage, QPainter, QFont, QColor
from PyQt5.QtCore import Qt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=str, default="")
    parser.add_argument("--right", type=str, default="")
    parser.add_argument("--border_color", type=str, default="black")
    parser.add_argument("--font_size", type=int, default=50)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    # Create QApplication in the main thread of this process
    app = QApplication(sys.argv)
    
    img = QImage(1920, 1080, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    
    painter = QPainter(img)
    font = QFont("Nirmala UI", args.font_size, QFont.Bold)
    painter.setFont(font)
    
    def draw_outlined_text(x, y, text, color_str):
        base_y = int(y) + int(args.font_size * 1.2)
        painter.setPen(QColor(args.border_color))
        for dx in [-2, 0, 2]:
            for dy in [-2, 0, 2]:
                if dx != 0 or dy != 0:
                    painter.drawText(int(x)+dx, base_y+dy, text)
        painter.setPen(QColor(color_str))
        painter.drawText(int(x), base_y, text)

    if args.left:
        draw_outlined_text(40, 40, args.left, "white")
    if args.right:
        draw_outlined_text(1920 - 400, 40, args.right, "white")
        
    painter.end()
    img.save(args.output)
    
if __name__ == "__main__":
    main()
