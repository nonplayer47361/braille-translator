# File: braille_translator/translator.py

import logging
import os
import re
import subprocess
from typing import TYPE_CHECKING, List, Literal, Optional, Tuple, Dict

import numpy as np
import cv2
import hgtk

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

# --- 상수 정의 ---
BRL_NEWLINE = chr(0x283F)       # ⠿ : 줄 바꿈
BRL_PARAGRAPH = chr(0x283E)     # ⠾ : 문단 구분 (줄바꿈 2번 의미)

# 언어 전환 코드 (Private Use Area의 문자를 사용)
BRL_SWITCH = {
    ("text", "ko"): chr(0xE000),
    ("text", "en"): chr(0xE001),
    ("text", "other"): chr(0xE002),
}

# 숫자 점자 <-> 숫자 문자 매핑
BRL_NUM_MAP = {
    '⠁': '1', '⠃': '2', '⠉': '3', '⠙': '4', '⠑': '5',
    '⠋': '6', '⠛': '7', '⠓': '8', '⠊': '9', '⠚': '0',
}
BRL_NUM_SIGN = '⠼'

# 출력 포맷을 위한 타입 정의
Format = Literal["unicode", "dots", "binary"]

LANGS = ("ko", "en", "other")
LANG_TABLE = {
    "ko": {"g1": "ko-g1.ctb", "g2": "ko-g2.ctb"},
    "en": {"g1": "en-us-g1.ctb", "g2": "en-us-g2.ctb"},
    "other": {"g1": "en-us-g1.ctb", "g2": "en-us-g2.ctb"},
}

RE_KO = re.compile(r"[가-힣]+")
RE_EN = re.compile(r"[A-Za-z]+")
RE_OT = re.compile(r"[^가-힣A-Za-z\s]+")

# --- 점자 유니코드 <-> 점 위치 표현 ---
def unicode_to_binary(unicode_str: str) -> str:
    return "".join(f"{ord(ch)-0x2800:06b}" if '\u2800' <= ch <= '\u28FF' else "000000" for ch in unicode_str)

def unicode_to_dots(unicode_str: str) -> str:
    parts = []
    for ch in unicode_str:
        if '\u2800' <= ch <= '\u28FF':
            code = ord(ch) - 0x2800
            dots = [str(i + 1) for i in range(6) if code & (1 << i)]
            parts.append("-".join(dots) if dots else "0")
        else:
            parts.append("0")
    return " ".join(parts)

def binary_to_unicode(binary_str: str) -> str:
    if len(binary_str) % 6 != 0:
        raise ValueError("Binary length must be multiple of 6")
    return "".join(chr(0x2800 + int(binary_str[i:i+6], 2)) for i in range(0, len(binary_str), 6))
# --- G2 축약어 로드 및 역매핑 구성 ---
def load_g2_contractions(table_dir: str) -> Dict[str, List[str]]:
    contractions = {}
    for lang, tbls in LANG_TABLE.items():
        g2_path = os.path.join(table_dir, tbls["g2"])
        if not os.path.exists(g2_path):
            contractions[lang] = []
            continue
        words = set()
        with open(g2_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(("always", "word", "contraction")):
                    parts = line.split()
                    if len(parts) >= 2:
                        word = parts[1].strip('"')
                        if re.match(r"^[A-Za-z가-힣]{2,}$", word):
                            words.add(word.lower())
        contractions[lang] = sorted(list(words))
    return contractions

def _run_cli(lou_path: str, table_dir: str, table: str, text: str, mode: str = "forward") -> str:
    cmd = [lou_path, "-b", f"{table_dir}/{table}", text]
    if mode == "backward":
        cmd.insert(1, "-r")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()

def _build_g2_reverse_map(lou_path: str, table_dir: str, g2_map: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    reverse_map = {}
    for lang, words in g2_map.items():
        table = LANG_TABLE[lang]["g2"]
        reverse_map[lang] = {}
        for word in words:
            try:
                braille = _run_cli(lou_path, table_dir, table, word, "forward")
                reverse_map[lang][braille] = word
            except Exception:
                continue
    return reverse_map
def validate_braille_sentence(braille: str) -> List[int]:
    """
    점자 문자열에서 문법적으로 잘못된 유니코드 점자 문자의 위치를 반환합니다.
    - 올바른 점자는 U+2800 ~ U+28FF 범위 내여야 하며
    - 각 문자별 비트 길이도 정확해야 합니다 (6비트 또는 확장 가능)
    """
    errors = []
    for i, ch in enumerate(braille):
        code = ord(ch)
        if not (0x2800 <= code <= 0x28FF):
            errors.append(i)
    return errors
# --- 메인 번역기 클래스 ---

class BrailleTranslator:
    def __init__(self, lou_translate: str = "bin/lou_translate.sh", table_dir: str = "tables"):
        self.lou_exec = lou_translate
        self.table_dir = table_dir
        self.g2_contractions = load_g2_contractions(table_dir)
        self.g2_reverse_map = _build_g2_reverse_map(self.lou_exec, self.table_dir, self.g2_contractions)

    def detect_language(self, text: str) -> str:
        if RE_KO.fullmatch(text):
            return "ko"
        elif RE_EN.fullmatch(text):
            return "en"
        else:
            return "other"

    def _apply_special_modes(self, lang: str, fragment: str) -> str:
        """숫자, 대문자 등 특수 모드를 감지하고 필요한 점자 기호를 추가합니다."""
        if lang == "other" and fragment.isdigit():
            # 숫자 모드 기호(⠼) 추가
            return chr(0x283C) + fragment
        
        if lang == "en" and fragment.isupper() and len(fragment) > 1:
            # 로마자 대문자 단어 기호(⠠⠠) 추가
            return chr(0x2820) * 2 + fragment
            
        return fragment

    def _split_by_lang(self, text: str) -> List[Tuple[str, str]]:
        """텍스트를 한글/영문/기타 언어 세그먼트로 분리합니다."""
        # 정규식: (한글+ | 영문+ | 그 외+)
        token_re = re.compile(r"([가-힣]+|[A-Za-z]+|[^가-힣A-Za-z]+)")
        tokens = []
        for fragment in token_re.findall(text):
            if not fragment:
                continue
            if RE_KO.fullmatch(fragment):
                tokens.append(("ko", fragment))
            elif RE_EN.fullmatch(fragment):
                tokens.append(("en", fragment))
            else:
                tokens.append(("other", fragment))
        return tokens

    def _split_by_lang_braille(self, line: str) -> List[Tuple[str, str]]:
        """점자 문자열을 언어 전환 코드를 기준으로 분리합니다."""
        segments: List[Tuple[str, str]] = []
        # BRL_SWITCH에서 역매핑 생성
        marker_to_lang = {marker: lang for (typ, lang), marker in BRL_SWITCH.items() if typ == "text"}
        
        # 기본 언어 설정 (첫 세그먼트의 언어를 결정하기 위함)
        cur_lang = "other"
        if line and line[0] in marker_to_lang:
             cur_lang = marker_to_lang[line[0]]

        buf = ""
        
        i = 0
        while i < len(line):
            char = line[i]
            if char in marker_to_lang:
                if buf:
                    segments.append((cur_lang, buf))
                # 언어 전환
                cur_lang = marker_to_lang[char]
                buf = ""
            else:
                buf += char
            i += 1
        
        if buf:
            segments.append((cur_lang, buf))
            
        return segments

    def text_to_braille(self, text: str, fmt: Format = "unicode") -> str:
        """
        주어진 텍스트를 점자로 변환합니다.
        - 문단 및 줄바꿈 반영
        - 언어 구간별 점자 전환 마커 삽입
        - 숫자 모드, 대문자 모드 등 특수 모드 처리
        - G2 → G1 테이블 fallback 처리
        """
        paragraphs = text.strip().split("\n\n")
        result = []
        
        for pi, para in enumerate(paragraphs):
            lines = para.splitlines()
            for li, line in enumerate(lines):
                for lang, fragment in self._split_by_lang(line):
                    result.append(BRL_SWITCH[("text", lang)])

                    # 숫자/대문자 등 특수 모드 처리
                    processed_fragment = self._apply_special_modes(lang, fragment)

                    tbl_g2 = LANG_TABLE[lang]["g2"]
                    tbl_g1 = LANG_TABLE[lang]["g1"]

                    # G2 → G1 fallback 점역 시도
                    try:
                        brl = _run_cli(self.lou_exec, self.table_dir, tbl_g2, processed_fragment, "forward")
                        if not brl or len(brl) < len(processed_fragment) // 2:
                            raise ValueError("G2 fallback triggered")
                    except Exception:
                        try:
                            brl = _run_cli(self.lou_exec, self.table_dir, tbl_g1, processed_fragment, "forward")
                        except Exception:
                            brl = ""

                    result.append(brl)

                # 줄바꿈 기호 삽입 (라인 사이에만)
                if li < len(lines) - 1:
                    result.append(BRL_NEWLINE)

            # 문단 구분 기호 삽입 (문단 사이에만)
            if pi < len(paragraphs) - 1:
                result.append(BRL_PARAGRAPH)

        braille_text = "".join(result)

        # 요청된 포맷에 따라 반환 형식 결정
        if fmt == "binary":
            return unicode_to_binary(braille_text)
        if fmt == "dots":
            return unicode_to_dots(braille_text)
        return braille_text

    def braille_to_text(self, braille: str) -> str:
        """
        점자 문자열을 일반 텍스트로 복원합니다.
        문단, 줄바꿈, 언어, 숫자, 대문자 모드를 모두 고려하여 복원합니다.
        문법 오류 감지 기능을 포함합니다.
        """
        # 문법 오류 감지
        invalid_positions = validate_braille_sentence(braille)
        if invalid_positions:
            logger.warning(f"점자 문법 오류 감지됨: 잘못된 문자 위치 {invalid_positions}")

        text = ""
        paragraphs = braille.strip().split(BRL_PARAGRAPH)

        for pi, para in enumerate(paragraphs):
            lines = para.split(BRL_NEWLINE)
            for li, line in enumerate(lines):
                for lang, brl_segment in self._split_by_lang_braille(line):
                    reverse_map = self.g2_reverse_map.get(lang, {})
                    cursor = 0
                    buffer = ""

                    while cursor < len(brl_segment):
                        matched = False
                        
                        # 1. 로마자 대문자 모드 확인
                        if lang == "en" and brl_segment[cursor:cursor+2] == '⠠⠠':
                            word_buffer = ""
                            word_cursor = cursor + 2
                            
                            while word_cursor < len(brl_segment):
                                char_to_decode = brl_segment[word_cursor]
                                try:
                                    restored = _run_cli(self.lou_exec, self.table_dir, LANG_TABLE[lang]["g2"], char_to_decode, "backward")
                                    word_buffer += restored
                                    word_cursor += 1
                                except Exception:
                                    break

                            if word_buffer:
                                buffer += word_buffer.upper()
                                cursor = word_cursor
                                matched = True

                        # 2. 숫자 모드 확인
                        if not matched and brl_segment[cursor] == BRL_NUM_SIGN:
                            num_buffer = ""
                            num_cursor = cursor + 1
                            while num_cursor < len(brl_segment) and brl_segment[num_cursor] in BRL_NUM_MAP:
                                num_buffer += BRL_NUM_MAP[brl_segment[num_cursor]]
                                num_cursor += 1
                            
                            if num_buffer:
                                buffer += num_buffer
                                cursor = num_cursor
                                matched = True

                        # 3. 축약어 우선 탐색
                        if not matched:
                            for end in range(len(brl_segment), cursor, -1):
                                piece = brl_segment[cursor:end]
                                if piece in reverse_map:
                                    buffer += reverse_map[piece]
                                    cursor = end
                                    matched = True
                                    break

                        # 4. 낱자 단위로 복원
                        if not matched:
                            raw_char = brl_segment[cursor]
                            try:
                                restored = _run_cli(self.lou_executable, self.tables_dir, LANG_TABLE[lang]["g2"], raw_char, "backward")
                            except Exception:
                                try:
                                    restored = _run_cli(self.lou_executable, self.tables_dir, LANG_TABLE[lang]["g1"], raw_char, "backward")
                                except Exception:
                                    restored = ""
                            buffer += restored
                            cursor += 1
                    
                    text += buffer

                if li < len(lines) - 1:
                    text += "\n"
            
            if pi < len(paragraphs) - 1:
                text += "\n\n"
                
        return text.strip()

    def text_to_braille_image(
        self,
        text: str,
        cell_size: int = 40,
        dot_radius: int = 6,
        margin: int = 20,
    ) -> "np.ndarray":
        """
        텍스트를 점자 이미지(numpy BGR 배열)로 변환합니다.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error(
                "이미지 생성을 위해 'opencv-python'과 'numpy'가 필요합니다. "
                "'pip install .[image]' 또는 'pip install opencv-python numpy'로 설치하세요."
            )
            raise

        if not text:
            return np.ones((margin * 2, margin * 2, 3), dtype=np.uint8) * 255

        braille_text = self.text_to_braille(text, fmt="unicode")
        lines = braille_text.split(BRL_NEWLINE)

        rows = len(lines)
        cols = max(len(line) for line in lines) if lines else 0

        h = rows * (cell_size + margin) + margin
        w = cols * (cell_size + margin) + margin
        img = np.ones((h, w, 3), dtype=np.uint8) * 255

        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                base_x = margin + c * (cell_size + margin)
                base_y = margin + r * (cell_size + margin)
                bits = unicode_to_binary(ch)

                for i, bit in enumerate(bits):
                    if bit == '1':
                        col_idx, row_idx = i % 2, i // 2
                        dx = base_x + (cell_size // 4) + (col_idx * (cell_size // 2))
                        dy = base_y + (cell_size // 6) + (row_idx * (cell_size // 3))
                        cv2.circle(img, (dx, dy), dot_radius, (0, 0, 0), -1)
        return img

    def image_to_binary(
        self, image: "np.ndarray", cell_size: int, margin: int, threshold: int = 128
    ) -> List[str]:
        """점자 이미지를 분석하여 이진 문자열 리스트로 변환합니다."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error("이미지 처리를 위해 'opencv-python'과 'numpy'가 필요합니다.")
            raise

        if image is None:
            logger.error("입력 이미지가 비어있습니다.")
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary_img = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

        img_h, img_w = binary_img.shape
        binary_cells = []
        
        # 이미지의 각 줄을 순회
        y = margin
        while y + cell_size <= img_h:
            x = margin
            while x + cell_size <= img_w:
                cell_bits = ""
                for i in range(6):
                    col_idx, row_idx = i % 2, i // 2
                    dot_x = x + (cell_size // 4) + (col_idx * (cell_size // 2))
                    dot_y = y + (cell_size // 6) + (row_idx * (cell_size // 3))
                    
                    if binary_img[dot_y, dot_x] != 0:
                        cell_bits += '1'
                    else:
                        cell_bits += '0'
                binary_cells.append(cell_bits)
                x += cell_size + margin
            y += cell_size + margin
            
        return binary_cells
    def image_to_braille(
            self, image: "np.ndarray", cell_size: int = 40, margin: int = 20, threshold: int = 128
    ) -> str:
        """
        점자 이미지를 유니코드 점자 문자열로 복원합니다.
        내부적으로 image_to_binary()를 호출하여 binary → unicode 변환을 수행합니다.
        """
        binary_cells = self.image_to_binary(image, cell_size, margin, threshold)
        unicode_braille = "".join(binary_to_unicode(bits) for bits in binary_cells)
        return unicode_braille

    def image_to_text(
        self,
        image: "np.ndarray",
        cell_size: int = 40,
        margin: int = 20,
        threshold: int = 128,
    ) -> str:
        """
        점자 이미지에서 일반 텍스트를 복원합니다.
        내부적으로 image_to_braille() → braille_to_text() 흐름을 따릅니다.
        """
        # 1단계: 점자 이미지 → 유니코드 점자 문자열
        unicode_braille = self.image_to_braille(
            image, cell_size=cell_size, margin=margin, threshold=threshold
        )

        # 2단계: 점자 문자열 → 일반 텍스트
        text = self.braille_to_text(unicode_braille)

        return text

    def shutdown(self, wait=True):
        """프로세스 풀을 안전하게 종료합니다."""