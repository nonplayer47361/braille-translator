#!/usr/bin/env python3
# File: main.py
# Description: 터미널 대화형 점자 번역/복원 도구

import sys
import os
import json
import logging
from typing import List

import cv2

from braille_translator.translator_v1 import (
    BrailleTranslator,
    unicode_to_dots,
    unicode_to_binary,
    binary_to_unicode,
)

# ── 설정 ───────────────────────────────────────────────────────────────────────────────
# 이미지 출력 파일명
IMG_OUT = "braille_output.png"
# JSON 바이너리 저장 경로
BIN_JSON = "braille_binary.json"
# 로깅 포맷
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def menu() -> None:
    print("\n=== 점자 번역기 ===")
    print("1. 번역 🔄")
    print("2. 복원 ↩️")
    print("3. 종료 ❌")


def translate_flow(tr: BrailleTranslator) -> None:
    txt = input("\n▶ 변환할 텍스트를 입력하세요:\n> ").strip()
    if not txt:
        logger.error("입력된 텍스트가 없습니다.")
        return

    try:
        # 1) 텍스트 → 유니코드 점자
        uni = tr.text_to_braille(txt, fmt="unicode")
        print(f"\n■ 유니코드 점자:\n{uni}")

        # 2) 점번호 리스트
        dots = unicode_to_dots(uni)
        print(f"\n■ 점번호 (dots):\n{dots}")

        # 3) 이진 배열 문자열 → 6개씩 분할
        bin_str = unicode_to_binary(uni)
        bin_chunks = [bin_str[i : i + 6] for i in range(0, len(bin_str), 6)]
        print(f"\n■ 이진화 배열:\n{bin_chunks}")

        # 4) 점자 이미지
        img = tr.text_to_braille_image(txt)
        cv2.imwrite(IMG_OUT, img)
        print(f"\n■ 점자 이미지 저장: {IMG_OUT}")

        # 5) JSON으로 바이너리 배열 저장
        with open(BIN_JSON, "w", encoding="utf-8") as f:
            json.dump(bin_chunks, f, ensure_ascii=False, indent=2)
        print(f"■ 이진배열 JSON 저장: {BIN_JSON}")

    except Exception as e:
        logger.exception("번역 중 오류가 발생했습니다.")


def restore_flow(tr: BrailleTranslator) -> None:
    print("\n▶ 복원할 입력 형식을 선택하세요:")
    print("1. 유니코드 점자 문자열")
    print("2. 이진배열(JSON 파일)")
    choice = input("> ").strip()

    try:
        if choice == "1":
            bri = input("\n▶ 유니코드 점자 문자열을 입력하세요:\n> ").strip()
            if not bri:
                logger.error("점자 문자열이 비어 있습니다.")
                return
            res = tr.braille_to_text(bri, fmt="unicode")

        elif choice == "2":
            path = input("\n▶ JSON 파일 경로를 입력하세요:\n> ").strip()
            if not os.path.isfile(path):
                logger.error(f"파일을 찾을 수 없습니다: {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                cells: List[List[int]] = json.load(f)
            res = tr.braille_to_text(cells, fmt="binary")

        else:
            logger.error("잘못된 선택입니다. 1 또는 2를 입력하세요.")
            return

        print(f"\n■ 복원된 텍스트:\n{res}")

    except Exception as e:
        logger.exception("복원 중 오류가 발생했습니다.")


def main():
    # Translator 초기화
    try:
        tr = BrailleTranslator()
        logger.info(f"점자 테이블 경로: {tr.tables_dir}")
    except Exception as e:
        logger.exception("BrailleTranslator 초기화에 실패했습니다.")
        sys.exit(1)

    # 메뉴 루프
    while True:
        menu()
        cmd = input("> ").strip()
        if cmd == "1":
            translate_flow(tr)
        elif cmd == "2":
            restore_flow(tr)
        elif cmd == "3":
            print("프로그램을 종료합니다.")
            break
        else:
            print("1, 2, 3 중에서 선택해주세요.")


if __name__ == "__main__":
    # OpenCV 쓰이는 부분 외에는 WARNING 이상의 로그만 보이도록 설정
    logging.getLogger("cv2").setLevel(logging.WARNING)
    main()