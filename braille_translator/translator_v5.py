# -*- coding: utf-8 -*-
"""
【 통합 점자 번역 시스템 V5 - Final 】
"""
import logging
import os
import re
import hashlib
from datetime import datetime
from typing import (
    TYPE_CHECKING, List, Literal, Optional, Any, Dict, Tuple
)
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# --- 라이브러리 임포트 ---
try:
    import numpy as np
    import cv2
    HAS_IMAGE_SUPPORT = True
except ImportError:
    np, cv2, HAS_IMAGE_SUPPORT = None, None, False
    logging.warning("이미지 처리를 위해 'opencv-python'과 'numpy' 설치를 권장합니다.")

try:
    import louis
except ImportError:
    logging.critical("'louis' 라이브러리가 필요합니다. 'pip install louis'로 설치해주세요.")
    raise

# --- 타입 및 로깅 설정 ---
if TYPE_CHECKING:
    import numpy
    NDArray = numpy.ndarray[Any, Any]
else:
    NDArray = Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 상수 및 타입 정의 ---
InputType = Literal["text", "unicode", "dots", "binary", "image"]
DEFAULT_TABLES = "ko-g2-fallback.ctb,en-us-g2-fallback.ctb"

# --- 데이터 클래스 정의 ---
@dataclass
class TranslationDetail:
    original_word: str
    braille_word: str
    is_contracted: bool

@dataclass
class UnifiedTranslationResult:
    original_text: str
    braille_unicode: str
    details: List[TranslationDetail]
    image_path: Optional[str] = None
    success: bool = True
    error_message: str = ""

    @property
    def braille_dots(self) -> str:
        return " ".join("-".join(str(i + 1) for i in range(6) if (ord(c) - 0x2800) & (1 << i)) or "0" if '\u2800' <= c <= '\u28FF' else c for c in self.braille_unicode)

    @property
    def braille_binary(self) -> str:
        return "".join(f"{ord(c)-0x2800:06b}" if '\u2800' <= c <= '\u28FF' else '000000' for c in self.braille_unicode)
        
    def to_display_dict(self) -> Dict[str, str]:
        return {
            "원본 텍스트": self.original_text,
            "점자 (유니코드)": self.braille_unicode,
            "점자 (점번호)": self.braille_dots,
            "점자 (이진)": self.braille_binary[:100] + ("..." if len(self.braille_binary) > 100 else ""),
            "생성된 이미지": self.image_path if self.image_path else "생성 안됨 (이미지 라이브러리 필요)",
            "성공 여부": "✓ 성공" if self.success else f"✗ 실패: {self.error_message}"
        }

# --- 헬퍼 클래스 및 함수 ---
class InputFormatDetector:
    @staticmethod
    def detect(input_data: str) -> InputType:
        if not input_data or not input_data.strip(): return "text"
        stripped = input_data.strip()
        if os.path.exists(stripped) and any(stripped.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']): return "image"
        non_space_chars = [c for c in stripped if not c.isspace()]
        if non_space_chars and all(0x2800 <= ord(c) <= 0x28FF for c in non_space_chars): return "unicode"
        if re.fullmatch(r'[\d\-\s]+', stripped) and any(c.isdigit() for c in stripped): return "dots"
        cleaned_bin = "".join(stripped.split())
        if len(cleaned_bin) > 5 and len(cleaned_bin) % 6 == 0 and all(c in '01' for c in cleaned_bin): return "binary"
        return "text"

def convert_to_unicode(input_data: str, input_type: InputType) -> str:
    if input_type == "dots":
        unicode_chars = []
        for part in input_data.strip().split():
            value = sum(1 << (int(d) - 1) for d in part.split('-') if d.isdigit() and 1 <= int(d) <= 6)
            unicode_chars.append(chr(0x2800 + value))
        return "".join(unicode_chars)
    elif input_type == "binary":
        binary_str = "".join(input_data.strip().split())
        return "".join(chr(0x2800 + int(binary_str[i:i+6], 2)) for i in range(0, len(binary_str), 6))
    return input_data

# --- 메인 통합 번역기 클래스 ---
class BrailleTranslator:  #<-- 【수정】 클래스 이름을 SuperBrailleTranslator에서 BrailleTranslator로 변경
    """통합 점자 번역기 V5 (liblouis 중심)"""

    def __init__(self, table_list: str = DEFAULT_TABLES, table_dir: Optional[str] = None):
        self.table_list = table_list
        self.history: List[UnifiedTranslationResult] = []
        if table_dir:
            os.environ['LOUIS_TABLEPATH'] = os.path.abspath(table_dir)
        try:
            louis.enableOnDemandCompilation()
        except Exception as e:
            logger.warning(f"louis.enableOnDemandCompilation() 호출 중 문제 발생: {e}")
        logger.info(f"BrailleTranslatorV5 초기화 완료. 테이블: {self.table_list}")

    def translate(self, text: str, generate_image: bool = True) -> UnifiedTranslationResult:
        if not text or not text.strip():
            return UnifiedTranslationResult(text, "", [], success=False, error_message="입력 텍스트가 비어있습니다.")
        
        logger.info(f"통합 번역 시작: '{text}' (이미지 생성: {generate_image})")
        try:
            braille_unicode, *_ = louis.translate(self.table_list, text)
            details = self._analyze_details(text)
            image_path = self._generate_image(braille_unicode, text) if generate_image and HAS_IMAGE_SUPPORT else None
            result = UnifiedTranslationResult(
                original_text=text, braille_unicode=braille_unicode, details=details, image_path=image_path, success=True
            )
            self.history.append(result)
            return result
        except Exception as e:
            logger.error(f"통합 번역 실패: {e}")
            return UnifiedTranslationResult(text, "", [], success=False, error_message=str(e))

    def restore(self, input_data: str) -> Tuple[str, InputType]:
        if not input_data or not input_data.strip(): return "", "text"
        detected_type = InputFormatDetector.detect(input_data)
        logger.info(f"통합 복원 시작: 감지된 입력타입={detected_type}")
        try:
            if detected_type == "image":
                if not HAS_IMAGE_SUPPORT: raise ImportError("이미지 처리 라이브러리가 없습니다.")
                braille_unicode = self._image_to_braille(input_data)
            else:
                braille_unicode = convert_to_unicode(input_data, detected_type)
            restored_text, *_ = louis.backTranslate(self.table_list, braille_unicode)
            return restored_text, detected_type
        except Exception as e:
            logger.error(f"통합 복원 실패: {e}")
            return f"[복원 실패: {e}]", detected_type

    def _analyze_details(self, text: str) -> List[TranslationDetail]:
        details = []
        words = re.split(r'(\s+)', text)
        g1_table = self.table_list.replace('-g2-fallback', '-g1')
        for word in words:
            if not word or word.isspace(): continue
            try:
                g2_word_braille, *_ = louis.translate(self.table_list, word)
                g1_word_braille, *_ = louis.translate(g1_table, word)
                is_contracted = (g2_word_braille != g1_word_braille)
                details.append(TranslationDetail(word, g2_word_braille, is_contracted))
            except Exception:
                details.append(TranslationDetail(word, word, False))
        return details

    def get_statistics(self) -> dict:
        if not self.history: return {"total_requests": 0, "message": "번역 이력이 없습니다."}
        total_requests = len(self.history)
        total_words = sum(len(r.details) for r in self.history)
        contracted_words = sum(sum(1 for d in r.details if d.is_contracted) for r in self.history)
        contraction_rate = (contracted_words / total_words * 100) if total_words > 0 else 0
        return {
            "total_requests": total_requests,
            "total_words_translated": total_words,
            "contracted_words": contracted_words,
            "contraction_rate_percent": round(contraction_rate, 2)
        }

    def _generate_image(self, braille_unicode: str, original_text: str, **kwargs) -> Optional[str]:
        settings = {'cell_size': 40, 'dot_radius': 6, 'margin': 20, 'cols_per_line': 25, **kwargs}
        image = self._create_braille_image_array(braille_unicode, original_text, settings)
        output_dir = "output_images"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"braille_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, image)
        logger.info(f"점자 이미지 생성 완료: {filepath}")
        return filepath
        
    def _create_braille_image_array(self, braille_unicode: str, original_text: str, settings: dict) -> NDArray:
        cell_size, dot_radius, margin, cols_per_line = [settings.get(k) for k in ['cell_size', 'dot_radius', 'margin', 'cols_per_line']]
        lines = [braille_unicode[i:i + cols_per_line] for i in range(0, len(braille_unicode), cols_per_line)]
        if not lines: lines = ['']
        rows, cols = len(lines), max(len(line) for line in lines) if lines else 0
        img_h, img_w = rows * cell_size + margin * (rows + 1), cols * cell_size + margin * (cols + 1)
        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 255
        dot_map = {0: (1, 1), 1: (1, 2), 2: (1, 3), 3: (2, 1), 4: (2, 2), 5: (2, 3)}
        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                if not ('\u2800' <= ch <= '\u28FF'): continue
                base_x, base_y = margin + c * (cell_size + margin), margin + r * (cell_size + margin)
                binary = f"{ord(ch) - 0x2800:06b}"[::-1]
                for i, bit in enumerate(binary):
                    if bit == '1':
                        dot_col, dot_row = dot_map[i]
                        dx, dy = base_x + (cell_size * dot_col // 3), base_y + (cell_size * dot_row // 4)
                        cv2.circle(img, (int(dx), int(dy)), dot_radius, (0, 0, 0), -1)
        return img

    def _image_to_braille(self, image_path: str, **kwargs) -> str:
        settings = {'cell_size': 40, 'margin': 20, 'threshold': 128, 'dot_radius': 6, **kwargs}
        if not os.path.exists(image_path): raise FileNotFoundError(f"이미지 파일 없음: {image_path}")
        image = cv2.imread(image_path)
        if image is None: raise ValueError("이미지 로드 실패")
        binary_cells = self._image_to_binary_cells(image, settings)
        return "".join(self.binary_to_unicode(bits) for bits in binary_cells if bits != "000000")

    def _image_to_binary_cells(self, image: NDArray, settings: dict) -> List[str]:
        cell_size, margin, threshold, dot_radius = [settings.get(k) for k in ['cell_size', 'margin', 'threshold', 'dot_radius']]
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
                    dot_x, dot_y = x + (cell_size * dot_col // 3), y + (cell_size * dot_row // 4)
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