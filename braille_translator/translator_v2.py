import cv2
import numpy as np
from numpy.typing import NDArray
from textwrap import wrap


# 유니코드 점자 문자를 6자리 2진수 문자열로 변환하는 함수
def unicode_to_binary(unicode_char: str) -> str:
    """
    유니코드 점자 문자를 6자리 2진수 문자열로 변환
    :param unicode_char: 점자 유니코드 문자
    :return: 6자리 binary 문자열 (e.g. '101010')
    """
    if not ('\u2800' <= unicode_char <= '\u28FF'):
        raise ValueError(f"유효하지 않은 점자 유니코드 문자입니다: {unicode_char}")
    bits = ord(unicode_char) - 0x2800
    return f"{bits:06b}".zfill(6)[::-1]

class BrailleTranslatorV2:
    def text_to_braille_image(self, text: str, dot_radius: int = 10, page_width_mm: float = 210.0, margin_mm: float = 15.0, auto_wrap: bool = True) -> np.ndarray:
        if not text:
            return np.ones((100, 100, 3), dtype=np.uint8) * 255

        usable_width_mm = page_width_mm - 2 * margin_mm
        max_cells_per_line = int(usable_width_mm // 6.0)  # 6mm 셀 간격 기준

        cell_spacing_x_mm = 6.0  # 셀 간격 수평 기준
        cell_spacing_y_mm = 10.0  # 셀 간격 수직 기준
        dot_spacing_x_mm = 2.5  # 점 간격 수평 기준
        dot_spacing_y_mm = 2.5  # 점 간격 수직 기준
        dot_diameter_mm = 1.6  # 점 지름 기준

        if auto_wrap:
            wrapped_lines = []
            for line in text.split("\n"):
                wrapped_lines.extend(wrap(line, width=max_cells_per_line))
            text = "\n".join(wrapped_lines)

        braille_lines = [self.text_to_braille(line, fmt="unicode") for line in text.split("\n")]
        rows = len(braille_lines)
        cols = max(len(line) for line in braille_lines)

        dpi = 10 * dot_radius  # mm to pixel conversion factor

        cell_width = int(cell_spacing_x_mm * dpi / 25.4)
        cell_height = int(cell_spacing_y_mm * dpi / 25.4)
        margin = int(margin_mm * dpi / 25.4)
        dot_spacing_x = int(dot_spacing_x_mm * dpi / 25.4)
        dot_spacing_y = int(dot_spacing_y_mm * dpi / 25.4)
        dot_radius_px = int(dot_diameter_mm * dpi / 25.4 / 2)

        img_h = rows * (cell_height + margin) + margin
        img_w = cols * (cell_width + margin) + margin
        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 255

        # 점자 도트 순서:
        # 1 (0,0), 2 (0,1), 3 (0,2),
        # 4 (1,0), 5 (1,1), 6 (1,2)
        dot_map = {0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (1, 0), 4: (1, 1), 5: (1, 2)}

        for row_idx, line in enumerate(braille_lines):
            for col_idx, ch in enumerate(line):
                if not ('\u2800' <= ch <= '\u28FF'):
                    continue
                cell_x = margin + col_idx * (cell_width + margin)
                cell_y = margin + row_idx * (cell_height + margin)
                # Calculate top-left corner of dots grid in the cell
                # The dots grid is 2 columns x 3 rows
                # Position dots relative to cell_x, cell_y
                binary = f"{ord(ch) - 0x2800:06b}"[::-1]
                for i, bit in enumerate(binary):
                    if bit == '1':
                        dot_col, dot_row = dot_map[i]
                        dx = cell_x + dot_col * dot_spacing_x + dot_radius_px
                        dy = cell_y + dot_row * dot_spacing_y + dot_radius_px
                        if 0 <= dx < img_w and 0 <= dy < img_h:
                            cv2.circle(img, (dx, dy), dot_radius_px, (0, 0, 0), -1)

        self._last_dot_radius = dot_radius
        self._last_cell_width = cell_width
        self._last_cell_height = cell_height
        self._last_margin = margin

        return img