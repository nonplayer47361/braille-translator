# File: braille_translator/translator.py

import os
import re
import sys
import shutil
import subprocess
import concurrent.futures
from importlib.resources import files
from typing import Any, List, Literal, Tuple, Optional, Dict

import numpy as np
import cv2
import hgtk

# --------------------------------------------------------------------
# 상수 및 패턴
# --------------------------------------------------------------------
Format = Literal["unicode", "dots", "binary"]
LANGS = ("ko", "en", "other")
LANG_TABLE = {
    "ko": {"g1": "ko-g1.ctb", "g2": "ko-g2.ctb"},
    "en": {"g1": "en-us-g1.ctb", "g2": "en-us-g2.ctb"},
    "other": {"g1": "en-us-g1.ctb", "g2": "en-us-g2.ctb"},
}
RE_KO    = re.compile(r"[가-힣]+")
RE_EN    = re.compile(r"[A-Za-z]+")
RE_OT    = re.compile(r"[^가-힣A-Za-z\s]+")

# language switch indicator (임의로 선택한 유니코드 점자)
BRL_SWITCH = {
    ("text", "ko"): chr(0x2820),     # ⠠
    ("text", "en"): chr(0x2830),     # ⠰
    ("braille","text"): chr(0x2800), # ⠀ (예시)
}

# --------------------------------------------------------------------
# G2 축약어 목록 동적 파싱 (예: 외부 JSON, CTB 파싱 등)
# --------------------------------------------------------------------
def load_g2_contractions(table_dir: str) -> Dict[str, List[str]]:
    """
    각 언어별 G2 CTB 파일에서 축약어 토큰 목록을 뽑아냅니다.
    실제 구현에서는 CTB 파일 혹은 별도 정의 파일을 파싱해야 합니다.
    여기서는 예시로 하드코딩하거나, 별도 JSON을 로드한다고 가정합니다.
    """
    # TODO: 실제 CTB 파싱 로직으로 교체
    return {
        "en": ["and", "the", "for", "of", "in", "to", "with", "over", "under"],
        "ko": [],  # 한글 G2 축약어 예: ["그럼", "그래서", ...]
    }

# --------------------------------------------------------------------
# liblouis CLI 호출 헬퍼
# --------------------------------------------------------------------
def _run_cli(
    lou_exec: str, tbl_dir: str, tbl: str, txt: str, mode: Literal["forward","backward"]
) -> str:
    flag = "--forward" if mode=="forward" else "--backward"
    disp = os.path.join(tbl_dir, "unicode.dis")
    cmd = [lou_exec, flag, "--display-table", disp, os.path.join(tbl_dir, tbl)]
    proc = subprocess.run(cmd, input=txt, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.rstrip("\n")

# --------------------------------------------------------------------
# 텍스트 토큰화
# --------------------------------------------------------------------
def tokenize_text(text: str) -> List[Tuple[str,str]]:
    tokens = []
    idx = 0
    while idx < len(text):
        for pat, lang in [(RE_KO,"ko"), (RE_EN,"en"), (RE_OT,"other")]:
            m = pat.match(text, idx)
            if m:
                tokens.append((m.group(), lang))
                idx = m.end()
                break
        else:
            tokens.append((text[idx], "other"))
            idx += 1
    return tokens

# --------------------------------------------------------------------
# BrailleTranslator
# --------------------------------------------------------------------
class BrailleTranslator:
    def __init__(
        self,
        lou: Optional[str]=None,
        tables: Optional[str]=None,
        max_workers: Optional[int]=None,
        default_contracted: bool=True
    ):
        # lou 경로
        self.lou = lou or self._find_cli()
        # liblouis 작업자 풀
        self.pool = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        # 테이블 디렉터리
        module_tbl = os.path.join(os.path.dirname(__file__), "tables")
        proj_tbl   = os.path.abspath(os.path.join(module_tbl, "..", "tables"))
        if tables and os.path.isdir(tables):
            self.tables = tables
        elif os.path.isdir(module_tbl):
            self.tables = module_tbl
        elif os.path.isdir(proj_tbl):
            self.tables = proj_tbl
        else:
            raise RuntimeError(f"테이블 디렉터리 없음: {tables!r}, {module_tbl!r}, {proj_tbl!r}")
        # 기본 G2 사용 여부
        self.default_contracted = default_contracted
        # G2 축약어 로드
        self.g2_map = load_g2_contractions(self.tables)

    def _find_cli(self) -> str:
        exe = "lou_translate.exe" if sys.platform.startswith("win") else "lou_translate"
        path = shutil.which(exe)
        if not path:
            raise FileNotFoundError(f"{exe} not found. Install liblouis CLI")
        return path

    # ----------------------------------------------------------------
    # text → braille
    # ----------------------------------------------------------------
    def text_to_braille(self, text: Any, fmt: Format="unicode") -> str:
        text = str(text)
        out_cells: List[str] = []

        # 1) 전체 텍스트 언어별로 토큰화
        tokens = tokenize_text(text)

        # 2) 언어 세그먼트별 처리
        for tok, lang in tokens:
            # 공백은 그대로
            if tok.isspace():
                out_cells.append(tok)
                continue

            # 2-1) G2 축약어 우선 매칭: 가장 긴 토큰찾기
            if lang in self.g2_map:
                # lower for English matching
                candidate = tok.lower() if lang=="en" else tok
                if candidate in self.g2_map[lang]:
                    tbl = LANG_TABLE[lang]["g2"]
                    br = self.pool.submit(_run_cli, self.lou, self.tables, tbl, tok, "forward").result()
                    out_cells.append(br)
                    continue

            # 2-2) 그렇지 않으면 G1(혹은 기본 컨트랙트 설정)으로
            tbl_key = "g2" if (lang in {"en","ko"} and self.default_contracted) else "g1"
            tbl = LANG_TABLE[lang][tbl_key]
            br = self.pool.submit(_run_cli, self.lou, self.tables, tbl, tok, "forward").result()

            # 2-3) 언어 전환 지시자
            out_cells.append(BRL_SWITCH[("text", lang)])
            out_cells.append(br)

        # 3) 포맷에 맞게 포맷팅
        braille = "".join(out_cells)
        if fmt == "dots":
            return unicode_to_dots(braille)
        if fmt == "binary":
            return unicode_to_binary(braille)
        return braille

    # ----------------------------------------------------------------
    # braille → text
    # ----------------------------------------------------------------
    def braille_to_text(self, braille: Any, fmt: Format="unicode") -> str:
        # 1) binary → unicode
        if fmt == "binary":
            from .translator import binary_to_unicode
            braille = binary_to_unicode("".join(str(b) for row in braille for b in row))

        # 2) 언어 전환 지시자 기준으로 분할
        segments: List[Tuple[str,str]] = []
        cur_lang = "other"
        buf = ""
        for ch in braille:
            # 전환 지시자 감지
            for (typ, lang), marker in BRL_SWITCH.items():
                if typ=="text" and ch == marker:
                    if buf:
                        segments.append((buf, cur_lang))
                    buf = ""
                    cur_lang = lang
                    break
            else:
                buf += ch
        if buf:
            segments.append((buf, cur_lang))

        # 3) 각 세그먼트 역번역
        result = []
        for seg, lang in segments:
            # 3-1) G2 축약어 역치환
            for contraction in sorted(self.g2_map.get(lang, []), key=len, reverse=True):
                # 점자 셀 → 텍스트 토큰
                tbl = LANG_TABLE[lang]["g2"]
                br = self.pool.submit(_run_cli, self.lou, self.tables, tbl, contraction, "forward").result()
                seg = seg.replace(br, contraction)

            # 3-2) 나머지 G1 역번역
            tbl = LANG_TABLE[lang]["g1"]
            for ch in seg:
                if '\u2800' <= ch <= '\u28FF':
                    back = self.pool.submit(_run_cli, self.lou, self.tables, tbl, ch, "backward").result()
                    if lang == "ko":
                        try:
                            result.append(hgtk.text.compose(back))
                        except hgtk.exception.NotHangulComposition:
                            result.append(back)
                    else:
                        result.append(back)
                else:
                    result.append(ch)

        return "".join(result)

    def shutdown(self, wait: bool=True):
        self.pool.shutdown(wait)

    def __enter__(self):  return self
    def __exit__(self, *args): self.shutdown()

# --------------------------------------------------------------------
# 유틸리티: unicode↔binary↔dots (위에는 중복이라 생략)
# --------------------------------------------------------------------
def unicode_to_binary(unicode_str: str) -> str:
    parts = []
    for ch in unicode_str:
        if '\u2800' <= ch <= '\u28FF':
            parts.append(f"{ord(ch)-0x2800:06b}")
        else:
            parts.append("000000")
    return "".join(parts)

def unicode_to_dots(unicode_str: str) -> str:
    parts = []
    for ch in unicode_str:
        if '\u2800' <= ch <= '\u28FF':
            code = ord(ch) - 0x2800
            dots = [str(i+1) for i in range(6) if code & (1<<i)]
            parts.append("-".join(dots) if dots else "0")
        else:
            parts.append("0")
    return " ".join(parts)