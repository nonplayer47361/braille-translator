# -*- coding: utf-8 -*-
import logging
import os
from typing import TYPE_CHECKING, List, Literal, Optional, Any

try:
    import numpy as np
    import cv2
except ImportError:
    np = None
    cv2 = None

try:
    import louis
except ImportError:
    logging.critical("'louis' 라이브러리가 필요합니다. 'pip install louis'로 설치해주세요.")
    raise

if TYPE_CHECKING:
    import numpy
    NDArray = numpy.ndarray[Any, Any]
else:
    NDArray = Any

logger = logging.getLogger(__name__)
Format = Literal["unicode", "dots", "binary"]
DEFAULT_TABLES = "ko-g2.ctb,en-us-g2.ctb"

# FALLBACK_TABLES = {
#     "ko": ("ko-g2.ctb", "ko-g1.ctb"),
#     "en": ("en-us-g2.ctb", "en-us-g1.ctb"),
#     "num": ("en-us-g2.ctb", "en-us-g1.ctb"),
#     "other": ("en-us-g2.ctb", "en-us-g1.ctb"),
# }

# --- 유틸리티 함수 ---

# 텍스트를 언어별로 분할하는 함수
import re
from typing import Tuple

def split_text_by_language(text: str) -> List[Tuple[str, str]]:
    """
    입력 문자열을 언어 유형(한글/영어/숫자/기타)별 블록으로 분할합니다.
    각 튜플은 (언어코드, 문자열) 형식입니다.
    """
    pattern = re.compile(
        r'(?P<ko>[가-힣\s]+)|(?P<en>[a-zA-Z\s]+)|(?P<num>[\d\s]+)|(?P<other>[^\w\s]+)'
    )
    blocks = []
    for match in pattern.finditer(text):
        for lang in ('ko', 'en', 'num', 'other'):
            segment = match.group(lang)
            if segment:
                blocks.append((lang, segment))
                break
    return blocks
def unicode_to_binary(s: str) -> str:
    """점자 유니코드를 6자리 이진수 문자열의 연속으로 변환합니다."""
    return "".join(f"{ord(c)-0x2800:06b}" if '\u2800' <= c <= '\u28FF' else '000000' for c in s)

def unicode_to_dots(s: str) -> str:
    """점자 유니코드를 점 위치(예: '1-3-5') 문자열로 변환합니다."""
    return " ".join("-".join(str(i + 1) for i in range(6) if (ord(c) - 0x2800) & (1 << i)) or "0" if '\u2800' <= c <= '\u28FF' else c for c in s)

def binary_to_unicode(s: str) -> str:
    """6자리 이진수 문자열을 점자 유니코드로 변환합니다."""
    if len(s) % 6 != 0:
        raise ValueError("Binary length must be multiple of 6")
    return "".join(chr(0x2800 + int(s[i:i + 6], 2)) for i in range(0, len(s), 6))

def validate_braille_sentence(s: str) -> List[int]:
    """점자 문자열의 유효성을 검사합니다."""
    return [i for i, c in enumerate(s) if not ('\u2800' <= c <= '\u28FF' or c.isspace())]


# --- 메인 번역기 클래스 ---
def parse_ctb_includes(ctb_path: str) -> List[str]:
    """CTB 파일 내부에서 포함된 .cti 또는 .ctb 파일 목록을 파싱합니다."""
    includes = []
    try:
        with open(ctb_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("include "):
                    include_file = line.split("include ")[1].strip()
                    includes.append(include_file)
    except FileNotFoundError:
        logger.warning(f"테이블 파일을 찾을 수 없습니다: {ctb_path}")
    except Exception as e:
        logger.error(f"CTB include 파싱 실패: {e}")
    return includes
class BrailleTranslatorV2:
    """텍스트-점자 변환 및 이미지 처리 기능을 제공하는 클래스 (V2)"""
    def __init__(self, table_dir: Optional[str] = None, table_list: str = DEFAULT_TABLES):
        self.table_list = table_list
        if table_dir:
            os.environ['LOUIS_TABLEPATH'] = os.path.abspath(table_dir)

        try:
            louis.enableOnDemandCompilation()
        except Exception as e:
            logger.warning(f"louis.enableOnDemandCompilation() 호출 중 문제 발생: {e}")

        logger.info(f"BrailleTranslatorV2 초기화 완료. 테이블: {self.table_list}")

        self.table_includes = {}
        for table in self.table_list.split(','):
            table_path = os.path.join(os.environ.get("LOUIS_TABLEPATH", ""), table)
            self.table_includes[table] = self._parse_all_includes(table_path)
            logger.info(f"{table} 에 포함된 전체 테이블 체인: {self.table_includes[table]}")

    def _parse_all_includes(self, ctb_path: str, visited=None) -> List[str]:
        """재귀적으로 포함된 모든 테이블을 추적합니다."""
        if visited is None:
            visited = set()
        result = []
        if not os.path.isfile(ctb_path):
            return result
        includes = parse_ctb_includes(ctb_path)
        for inc in includes:
            if inc not in visited:
                visited.add(inc)
                result.append(inc)
                child_path = os.path.join(os.environ.get("LOUIS_TABLEPATH", ""), inc)
                result.extend(self._parse_all_includes(child_path, visited))
        return result

    def _get_table_by_lang(self, lang: str) -> str:
        """언어별 테이블 우선순위를 반환합니다."""
        primary, fallback = None, None
        return primary if primary else ""

    def _fallback_to_g1_tables(self, tables: str) -> str:
        """현재 G2 테이블 리스트를 G1 테이블 리스트로 안전하게 변환합니다."""
        return ",".join(
            t.replace("-g2.ctb", "-g1.ctb") if "-g2.ctb" in t else t
            for t in tables.split(',')
        )

    def text_to_braille(self, text: str, fmt: Format = "unicode") -> str:
        if not text:
            return ""
        results = []

        for lang, chunk in split_text_by_language(text):
            tables_to_try = []
            for base_table in self.table_list.split(','):
                tables_to_try.append(base_table)
                includes = self.table_includes.get(base_table, [])
                tables_to_try.extend([t for t in includes if t not in tables_to_try])

            braille_chunk = ""
            for table in tables_to_try:
                try:
                    result, *_ = louis.translate(table, chunk)
                    if result:  # 변환 결과가 있는 경우
                        braille_chunk = result
                        logger.debug(f"{lang.upper()} 변환 성공 (테이블: {table})")
                        break
                    else:
                        logger.debug(f"{lang.upper()} 변환 결과 없음 (테이블: {table})")
                except RuntimeError as e:
                    logger.debug(f"{lang.upper()} 변환 실패 (테이블: {table}): {e}")
            results.append(braille_chunk)

        braille_text = "".join(results)
        if fmt == "binary":
            return unicode_to_binary(braille_text)
        if fmt == "dots":
            return unicode_to_dots(braille_text)
        return braille_text

    def braille_to_text(self, braille: str) -> str:
        """점자를 텍스트로 복원합니다. G2 실패 시 G1 테이블로 fallback합니다."""
        if not braille:
            return ""
        invalid_positions = validate_braille_sentence(braille)
        if invalid_positions:
            logger.warning(f"점자 문법 오류 감지됨: 위치 {invalid_positions}에 잘못된 문자가 있습니다.")
        try:
            text, *_ = louis.backTranslate(self.table_list, braille)
        except RuntimeError as e:
            logger.warning(f"G2 복원 실패: {e}. G1 테이블로 재시도합니다.")
            try:
                fallback_tables = self._fallback_to_g1_tables(self.table_list)
                text, *_ = louis.backTranslate(fallback_tables, braille)
            except RuntimeError as e2:
                logger.error(f"G1 복원도 실패: {e2}")
                return braille
        return text

    def text_to_braille_image(self, text: str, cell_size: int = 40, dot_radius: int = 6, margin: int = 20, cols_per_line: int = 30) -> NDArray:
        """텍스트를 점자 이미지로 변환합니다."""
        if cv2 is None or np is None:
            raise ImportError("이미지 생성을 위해 'opencv-python'과 'numpy'가 필요합니다.")
        if not text:
            return np.ones((margin * 2, margin * 2, 3), dtype=np.uint8) * 255
            
        braille_text = self.text_to_braille(text, fmt="unicode")
        lines = [braille_text[i:i + cols_per_line] for i in range(0, len(braille_text), cols_per_line)]
        rows, cols = len(lines), max(len(line) for line in lines) if lines else 0
        
        img_h = rows * cell_size + margin * (rows + 1)
        img_w = cols * cell_size + margin * (cols + 1)
        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 255
        
        dot_map = {0: (1, 1), 1: (1, 2), 2: (1, 3), 3: (2, 1), 4: (2, 2), 5: (2, 3)}

        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                if not ('\u2800' <= ch <= '\u28FF'):
                    continue
                base_x = margin + c * (cell_size + margin)
                base_y = margin + r * (cell_size + margin)
                binary = f"{ord(ch) - 0x2800:06b}"[::-1]
                for i, bit in enumerate(binary):
                    if bit == '1':
                        dot_col, dot_row = dot_map[i]
                        dx = base_x + (cell_size * dot_col // 3)
                        dy = base_y + (cell_size * dot_row // 4)
                        cv2.circle(img, (int(dx), int(dy)), dot_radius, (0, 0, 0), -1)
        return img

    def image_to_text(self, image: NDArray, cell_size: int = 40, margin: int = 20, threshold: int = 128, dot_radius: int = 6) -> str:
        """점자 이미지에서 텍스트를 복원합니다."""
        if cv2 is None or np is None:
            raise ImportError("이미지 처리를 위해 'opencv-python'과 'numpy'가 필요합니다.")
        unicode_braille = self.image_to_braille(image, cell_size, margin, threshold, dot_radius)
        return self.braille_to_text(unicode_braille)

    def image_to_braille(self, image: NDArray, cell_size: int = 40, margin: int = 20, threshold: int = 128, dot_radius: int = 6) -> str:
        """점자 이미지에서 유니코드 점자 문자열을 추출합니다."""
        binary_cells = self._image_to_binary_cells(image, cell_size, margin, threshold, dot_radius)
        return "".join(binary_to_unicode(bits) for bits in binary_cells if bits != "000000")

    def _image_to_binary_cells(self, image: NDArray, cell_size: int = 40, margin: int = 20, threshold: int = 128, dot_radius: int = 6) -> List[str]:
        """점자 이미지를 분석하여 각 셀을 이진 문자열 리스트로 변환합니다."""
        if image is None:
            logger.error("입력 이미지가 비어있습니다."); return []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary_img = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
        
        img_h, img_w = binary_img.shape
        binary_cells, dot_map = [], {0: (1, 1), 1: (1, 2), 2: (1, 3), 3: (2, 1), 4: (2, 2), 5: (2, 3)}
        
        y = margin
        while y + cell_size <= img_h:
            x = margin
            while x + cell_size <= img_w:
                bits = ""
                for i in range(6):
                    dot_col, dot_row = dot_map[i]
                    dot_x = x + (cell_size * dot_col // 3)
                    dot_y = y + (cell_size * dot_row // 4)
                    
                    radius = max(1, dot_radius // 2)
                    check_x, check_y = int(dot_x), int(dot_y)

                    if check_y < img_h and check_x < img_w:
                        roi = binary_img[check_y - radius : check_y + radius, check_x - radius : check_x + radius]
                        bits = ('1' if np.any(roi) else '0') + bits
                    else:
                        bits = '0' + bits
                
                binary_cells.append(bits)
                x += cell_size + margin
            y += cell_size + margin

        return binary_cells