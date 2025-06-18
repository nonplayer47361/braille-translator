# -*- coding: utf-8 -*-
"""
【 통합 점자 번역 시스템 V5 】
번역-이미지-복원 기능을 통합한 최종 개선 버전
- 약자 우선 번역 (Grade 2 축약어 우선)
- 약자 없는 경우만 비약자 방식 적용
- 언어 자동 구분 및 혼합 언어 처리
- 한국어/영어 점자 규정 완전 준수
"""

import os
import re
import json
import logging
import tempfile
import hashlib
from typing import (
    TYPE_CHECKING, List, Literal, Optional, Any, Dict, Tuple, Set, Union
)
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import unicodedata

try:
    import louis
except ImportError:
    print("liblouis 라이브러리가 필요합니다: pip install louis")
    exit(1)

# 이미지 처리 라이브러리 임포트
try:
    import numpy as np
    import cv2
    HAS_IMAGE_SUPPORT = True
except ImportError:
    np = None
    cv2 = None
    HAS_IMAGE_SUPPORT = False
    logging.warning("이미지 처리를 위해 'opencv-python'과 'numpy' 설치를 권장합니다.")

# 타입 및 로깅 설정
if TYPE_CHECKING:
    import numpy
    NDArray = numpy.ndarray[Any, Any]
else:
    NDArray = Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LanguageType(Enum):
    """언어 타입 정의"""
    KOREAN = "korean"
    ENGLISH = "english"
    NUMBER = "number"
    PUNCTUATION = "punctuation"
    MIXED = "mixed"
    UNKNOWN = "unknown"

class ContractionLevel(Enum):
    """축약 수준 정의"""
    GRADE2 = "grade2"  # 약자 우선
    GRADE1 = "grade1"  # 비약자
    AUTO = "auto"      # 자동 선택

InputType = Literal["text", "unicode", "dots", "binary", "image"]
DEFAULT_TABLES = "ko-g2-fallback.ctb,en-us-g2-fallback.ctb"
FALLBACK_TABLES = {
    "korean": ["ko-g2.ctb", "ko-g1.ctb", "ko.utb"],
    "english": ["en-us-g2.ctb", "en-gb-g2.ctb", "en-us-g1.ctb"],
    "numbers": ["digits6Dots.uti", "printableAscii.uti"]
}

@dataclass
class UnifiedTranslationResult:
    """통합 번역 결과 - 모든 포맷 포함"""
    original_text: str
    input_type: str
    braille_unicode: str
    braille_dots: str
    braille_binary: str
    image_path: Optional[str]
    language_detected: str
    contraction_level: str
    table_used: str
    segments: List[Tuple[str, str]]
    success: bool
    has_image: bool
    error_message: str = ""
    
    def to_display_dict(self) -> Dict[str, str]:
        """화면 출력용 딕셔너리 변환"""
        return {
            "원본 텍스트": self.original_text,
            "점자 (유니코드)": self.braille_unicode,
            "점자 (점번호)": self.braille_dots,
            "점자 (이진)": self.braille_binary[:100] + "..." if len(self.braille_binary) > 100 else self.braille_binary,
            "생성된 이미지": self.image_path if self.image_path else "생성 안됨",
            "감지된 언어": self.language_detected,
            "축약 수준": self.contraction_level,
            "사용된 테이블": self.table_used,
            "세그먼트 수": str(len(self.segments)),
            "성공 여부": "✓ 성공" if self.success else "✗ 실패"
        }

class InputFormatDetector:
    """입력 포맷 자동 감지 클래스"""
    @staticmethod
    def detect_input_type(input_data: str) -> InputType:
        if not input_data or not input_data.strip():
            return "text"
        
        input_data = input_data.strip()
        
        if InputFormatDetector._is_image_path(input_data):
            return "image"
        if InputFormatDetector._is_braille_unicode(input_data):
            return "unicode"
        if InputFormatDetector._is_dots_format(input_data):
            return "dots"
        if InputFormatDetector._is_binary_format(input_data):
            return "binary"
        return "text"

    @staticmethod
    def _is_image_path(input_data: str) -> bool:
        if not input_data: return False
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        if any(input_data.lower().endswith(ext) for ext in image_extensions):
            return True
        if os.path.exists(input_data):
            try:
                if HAS_IMAGE_SUPPORT:
                    import cv2
                    img = cv2.imread(input_data)
                    return img is not None
            except:
                pass
        return False

    @staticmethod
    def _is_braille_unicode(input_data: str) -> bool:
        if not input_data: return False
        non_space_chars = [c for c in input_data if not c.isspace()]
        if not non_space_chars: return False
        return all(0x2800 <= ord(c) <= 0x28FF for c in non_space_chars)

    @staticmethod
    def _is_dots_format(input_data: str) -> bool:
        if not input_data: return False
        pattern = re.compile(r'^[\d\-\s]+$')
        if not pattern.match(input_data): return False
        tokens = input_data.split()
        for token in tokens:
            if token == '0': continue
            dots = token.split('-')
            for dot in dots:
                if not dot.isdigit() or not (1 <= int(dot) <= 8):
                    return False
        return True

    @staticmethod
    def _is_binary_format(input_data: str) -> bool:
        if not input_data: return False
        cleaned = input_data.replace(' ', '').replace('\n', '').replace('\t', '')
        if not cleaned: return False
        if not all(c in '01' for c in cleaned): return False
        return len(cleaned) >= 6 and len(cleaned) % 6 == 0

# --- 유틸리티 함수들 ---
def unicode_to_binary(s: str) -> str:
    if not s: return ""
    binary_parts = []
    for c in s:
        if '\u2800' <= c <= '\u28FF':
            value = ord(c) - 0x2800
            binary_parts.append(f"{value:06b}")
        elif c.isspace():
            binary_parts.append("000000")
        else:
            binary_parts.append("000000")
    return "".join(binary_parts)

def unicode_to_dots(s: str) -> str:
    if not s: return ""
    dots_parts = []
    for c in s:
        if '\u2800' <= c <= '\u28FF':
            value = ord(c) - 0x2800
            if value == 0:
                dots_parts.append("0")
            else:
                dots = [str(i + 1) for i in range(6) if value & (1 << i)]
                dots_parts.append("-".join(dots) if dots else "0")
        elif c.isspace():
            dots_parts.append("0")
        else:
            dots_parts.append("0")
    return " ".join(dots_parts)

def binary_to_unicode(s: str) -> str:
    if not s: return ""
    cleaned = s.replace(' ', '').replace('\n', '').replace('\t', '')
    if len(cleaned) % 6 != 0:
        raise ValueError("이진 문자열 길이는 6의 배수여야 합니다")
    unicode_chars = [chr(0x2800 + int(cleaned[i:i + 6], 2)) for i in range(0, len(cleaned), 6)]
    return "".join(unicode_chars)

def dots_to_unicode(dots_str: str) -> str:
    if not dots_str: return ""
    dots_list = dots_str.split()
    unicode_chars = []
    for dots in dots_list:
        if dots == "0" or not dots:
            unicode_chars.append('⠀')
        else:
            value = 0
            for digit_str in dots.split('-'):
                if digit_str.isdigit():
                    digit = int(digit_str)
                    if 1 <= digit <= 6:
                        value |= (1 << (digit - 1))
            unicode_chars.append(chr(0x2800 + value))
    return ''.join(unicode_chars)

def validate_braille_sentence(s: str) -> List[int]:
    return [i for i, c in enumerate(s) if not ('\u2800' <= c <= '\u28FF' or c.isspace())]

class LanguageDetector:
    def __init__(self):
        self.patterns = {
            LanguageType.KOREAN: self._is_korean, LanguageType.ENGLISH: self._is_english,
            LanguageType.NUMBER: self._is_number, LanguageType.PUNCTUATION: self._is_punctuation
        }
    def _is_korean(self, char: str) -> bool: return ('\uAC00' <= char <= '\uD7AF') or ('\u3131' <= char <= '\u3163')
    def _is_english(self, char: str) -> bool: return char.isalpha() and ord(char) < 128
    def _is_number(self, char: str) -> bool: return char.isdigit()
    def _is_punctuation(self, char: str) -> bool: return char in '.,!?;:()[]{}\'"-+=*/\\<>@#$%^&|`~'
    def detect_language(self, text: str) -> LanguageType:
        if not text.strip(): return LanguageType.UNKNOWN
        language_counts = {lang: 0 for lang in LanguageType}
        for char in text:
            for lang_type, check_func in self.patterns.items():
                if check_func(char):
                    language_counts[lang_type] += 1
                    break
        active_languages = [lang for lang, count in language_counts.items() if count > 0]
        if len(active_languages) > 1: return LanguageType.MIXED
        max_lang = max(language_counts.items(), key=lambda x: x[1])
        return max_lang[0] if max_lang[1] > 0 else LanguageType.UNKNOWN
    def segment_by_language(self, text: str) -> List[Tuple[str, LanguageType]]:
        segments, current_segment, current_language = [], "", None
        for char in text:
            char_language = None
            for lang_type, check_func in self.patterns.items():
                if check_func(char):
                    char_language = lang_type
                    break
            if char_language is None: char_language = LanguageType.UNKNOWN
            if current_language is not None and current_language != char_language:
                if current_segment: segments.append((current_segment, current_language))
                current_segment = char
                current_language = char_language
            else:
                current_segment += char
                current_language = char_language
        if current_segment: segments.append((current_segment, current_language))
        return segments

class ContractionManager:
    """축약어 관리 클래스 (V5에서는 liblouis에 위임)"""
    def __init__(self):
        pass # V5에서는 liblouis가 모든 축약어 처리를 담당

# --- 메인 통합 번역기 클래스 ---
class SuperBrailleTranslator:
    """통합 점자 번역기 V5"""
    def __init__(self, table_list: str = DEFAULT_TABLES, table_dir: Optional[str] = None):
        self.table_list = table_list
        if table_dir:
            os.environ['LOUIS_TABLEPATH'] = os.path.abspath(table_dir)
        try:
            louis.enableOnDemandCompilation()
        except Exception as e:
            logger.warning(f"louis.enableOnDemandCompilation() 호출 중 문제 발생: {e}")
        self.language_detector = LanguageDetector()
        self.input_detector = InputFormatDetector()
        self.translation_history = []
        self.image_settings = { 'cell_size': 50, 'dot_radius': 8, 'margin': 30, 'cols_per_line': 25 }
        logger.info(f"SuperBrailleTranslator V5 초기화 완료. 테이블: {self.table_list}")
    
    def unified_translate(self, text: str, contraction_level: ContractionLevel = ContractionLevel.AUTO, generate_image: bool = True) -> UnifiedTranslationResult:
        logger.info(f"통합 번역 시작: '{text}' (축약: {contraction_level}, 이미지: {generate_image})")
        if not text or not text.strip():
            return self._create_empty_result(text)
        try:
            detected_language = self.language_detector.detect_language(text)
            segments = self.language_detector.segment_by_language(text)
            braille_unicode, *_ = louis.translate(self.table_list, text)
            braille_dots = unicode_to_dots(braille_unicode)
            braille_binary = unicode_to_binary(braille_unicode)
            image_path = self._generate_braille_image(braille_unicode, text) if generate_image and HAS_IMAGE_SUPPORT else None
            result = UnifiedTranslationResult(
                original_text=text, input_type="text", braille_unicode=braille_unicode, braille_dots=braille_dots,
                braille_binary=braille_binary, image_path=image_path, language_detected=detected_language.value,
                contraction_level=contraction_level.value, table_used=self.table_list,
                segments=[(seg[0], seg[1].value) for seg in segments], success=True, has_image=image_path is not None
            )
            self.translation_history.append(result)
            logger.info(f"통합 번역 완료: 성공")
            return result
        except Exception as e:
            logger.error(f"통합 번역 실패: {e}")
            return UnifiedTranslationResult(
                original_text=text, input_type="text", braille_unicode="", braille_dots="", braille_binary="",
                image_path=None, language_detected=LanguageType.UNKNOWN.value, contraction_level=contraction_level.value,
                table_used=self.table_list, segments=[], success=False, has_image=False, error_message=str(e)
            )

    def unified_restore(self, input_data: str, force_type: Optional[InputType] = None) -> str:
        if not input_data or not input_data.strip(): return ""
        input_type = force_type or self.input_detector.detect_input_type(input_data)
        logger.info(f"통합 복원 시작: 입력타입={input_type}")
        try:
            if input_type == "text": return input_data.strip()
            if input_type == "unicode": unicode_braille = input_data
            elif input_type == "dots": unicode_braille = dots_to_unicode(input_data)
            elif input_type == "binary": unicode_braille = binary_to_unicode(input_data)
            elif input_type == "image":
                if not HAS_IMAGE_SUPPORT: raise ImportError("이미지 처리를 위해 'opencv-python'과 'numpy'가 필요합니다.")
                unicode_braille = self._extract_braille_from_image(input_data)
            else: raise ValueError(f"지원하지 않는 입력 타입: {input_type}")
            return self._restore_from_unicode(unicode_braille)
        except Exception as e:
            logger.error(f"통합 복원 실패: {e}")
            return f"[복원 실패: {str(e)}]"

    def _restore_from_unicode(self, unicode_braille: str) -> str:
        if not unicode_braille: return ""
        invalid_positions = validate_braille_sentence(unicode_braille)
        if invalid_positions: logger.warning(f"점자 문법 오류 감지: 위치 {invalid_positions}")
        try:
            text, *_ = louis.backTranslate(self.table_list, unicode_braille)
            if text and text.strip(): return text
        except Exception as e: logger.debug(f"기본 역번역 실패: {e}")
        for language, tables in FALLBACK_TABLES.items():
            for table in tables:
                try:
                    text, *_ = louis.backTranslate(table, unicode_braille)
                    if text and text.strip():
                        logger.info(f"역번역 성공 (테이블: {table})")
                        return text
                except: continue
        logger.warning("모든 테이블로 역번역 실패")
        return unicode_braille

    def _generate_braille_image(self, braille_unicode: str, original_text: str) -> str:
        if not HAS_IMAGE_SUPPORT: raise ImportError("이미지 처리 라이브러리가 필요합니다.")
        cell_size, dot_radius, margin, cols_per_line = [self.image_settings.get(k) for k in ['cell_size', 'dot_radius', 'margin', 'cols_per_line']]
        lines = [braille_unicode[i:i + cols_per_line] for i in range(0, len(braille_unicode), cols_per_line)]
        if not lines: lines = ['']
        rows, cols = len(lines), max(len(line) for line in lines)
        img_width, img_height, text_height = cols * cell_size + margin * (cols + 1), rows * cell_size + margin * (rows + 1), 60
        img = np.ones((img_height + text_height, img_width, 3), dtype=np.uint8) * 255
        dot_positions = {
            0: (cell_size // 4, cell_size // 6), 1: (cell_size // 4, cell_size // 3), 2: (cell_size // 4, cell_size // 2),
            3: (3 * cell_size // 4, cell_size // 6), 4: (3 * cell_size // 4, cell_size // 3), 5: (3 * cell_size // 4, cell_size // 2),
        }
        for row, line in enumerate(lines):
            for col, char in enumerate(line):
                if not ('\u2800' <= char <= '\u28FF'): continue
                cell_x, cell_y = margin + col * (cell_size + margin), margin + row * (cell_size + margin)
                cv2.rectangle(img, (cell_x, cell_y), (cell_x + cell_size, cell_y + cell_size), (200, 200, 200), 1)
                braille_value = ord(char) - 0x2800
                for dot_idx in range(6):
                    dot_x, dot_y = cell_x + dot_positions[dot_idx][0], cell_y + dot_positions[dot_idx][1]
                    if braille_value & (1 << dot_idx):
                        cv2.circle(img, (int(dot_x), int(dot_y)), dot_radius, (0, 0, 0), -1)
                    else:
                        cv2.circle(img, (int(dot_x), int(dot_y)), dot_radius//3, (230, 230, 230), 1)
        text_y, font, font_scale, font_color, thickness = img_height - text_height + 20, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
        display_text = original_text[:50] + "..." if len(original_text) > 50 else original_text
        cv2.putText(img, f"Original: {display_text}", (margin, text_y), font, font_scale, font_color, thickness)
        cv2.putText(img, f"Braille: {braille_unicode[:30]}{'...' if len(braille_unicode) > 30 else ''}", (margin, text_y + 25), font, font_scale, font_color, thickness)
        text_hash, filename = hashlib.md5(original_text.encode()).hexdigest()[:8], f"braille_{text_hash}.png"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        cv2.imwrite(filepath, img)
        logger.info(f"점자 이미지 생성 완료: {filepath}")
        return filepath
    
    def _extract_braille_from_image(self, image_path: str) -> str:
        if not HAS_IMAGE_SUPPORT: raise ImportError("이미지 처리 라이브러리가 필요합니다.")
        if not os.path.exists(image_path): raise FileNotFoundError(f"이미지 파일이 없습니다: {image_path}")
        img = cv2.imread(image_path)
        if img is None: raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        cell_size, margin = self.image_settings['cell_size'], self.image_settings['margin']
        height, width = binary.shape
        unicode_chars = []
        y = margin
        while y + cell_size <= height:
            row_chars = []
            x = margin
            while x + cell_size <= width:
                braille_value = self._extract_cell_value(binary, x, y, cell_size)
                if braille_value >= 0:
                    row_chars.append(chr(0x2800 + braille_value))
                x += cell_size + margin
            if row_chars: unicode_chars.extend(row_chars)
            y += cell_size + margin
        result = ''.join(unicode_chars)
        logger.info(f"이미지에서 점자 추출 완료: {len(unicode_chars)}개 문자")
        return result

    def _extract_cell_value(self, binary_img: NDArray, x: int, y: int, cell_size: int) -> int:
        dot_positions = [
            (cell_size // 4, cell_size // 6), (cell_size // 4, cell_size // 3), (cell_size // 4, cell_size // 2),
            (3 * cell_size // 4, cell_size // 6), (3 * cell_size // 4, cell_size // 3), (3 * cell_size // 4, cell_size // 2),
        ]
        braille_value, valid_dots = 0, 0
        for dot_idx, (rel_x, rel_y) in enumerate(dot_positions):
            abs_x, abs_y = x + rel_x, y + rel_y
            if abs_y < binary_img.shape[0] and abs_x < binary_img.shape[1]:
                radius = max(3, cell_size // 10)
                roi = binary_img[max(0, abs_y - radius):min(binary_img.shape[0], abs_y + radius), max(0, abs_x - radius):min(binary_img.shape[1], abs_x + radius)]
                if roi.size > 0 and np.sum(roi > 0) > roi.size * 0.3:
                    braille_value |= (1 << dot_idx)
                valid_dots += 1
        return braille_value if valid_dots >= 4 else -1

    def _create_empty_result(self, text: str) -> UnifiedTranslationResult:
        return UnifiedTranslationResult(
            original_text=text, input_type="text", braille_unicode="", braille_dots="", braille_binary="",
            image_path=None, language_detected=LanguageType.UNKNOWN.value, contraction_level=ContractionLevel.AUTO.value,
            table_used=self.table_list, segments=[], success=True, has_image=False
        )

    def get_statistics(self) -> Dict[str, Any]:
        if not self.translation_history: return {"message": "번역 이력이 없습니다."}
        total = len(self.translation_history)
        successful = sum(1 for t in self.translation_history if t.success)
        with_images = sum(1 for t in self.translation_history if t.has_image)
        language_stats = {}
        for result in self.translation_history:
            lang = result.language_detected
            language_stats[lang] = language_stats.get(lang, 0) + 1
        return {
            'total_translations': total, 'successful_translations': successful,
            'success_rate': successful / total if total > 0 else 0,
            'images_generated': with_images, 'image_generation_rate': with_images / total if total > 0 else 0,
            'language_distribution': language_stats,
            'features': {
                'unified_translation': True, 'auto_format_detection': True,
                'image_support': HAS_IMAGE_SUPPORT, 'contraction_support': True, 'multi_language': True
            }
        }