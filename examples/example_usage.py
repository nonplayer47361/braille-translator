#!/usr/bin/env python3
# File: examples/example_usage.py
# Brief: BrailleTranslator 클래스 사용 예시
# Usage:
#   python example_usage.py to-braille -f unicode "Hello 안녕 123!"
#   python example_usage.py to-braille -f dots "Hello"
#   python example_usage.py to-braille -f binary "안녕"
#   python example_usage.py to-text -f unicode "⠠⠓⠑⠇⠇⠕"
#   python example_usage.py to-text -f binary cells.json
#   python example_usage.py to-image "안녕하세요" -o out.png
#   python example_usage.py from-image out.png

import argparse
import sys
import json
import cv2

from braille_translator.translator import BrailleTranslator

def cmd_to_braille(args, tr: BrailleTranslator):
    text = args.text or sys.stdin.read().rstrip("\n")
    out = tr.text_to_braille(text, fmt=args.format)
    # binary 포맷이면 JSON 배열로 출력
    if args.format == "binary":
        # text_to_braille -> binary returns a flat string of bits,
        # 테스트용으로 6비트씩 분할해 cell 리스트로 변환
        bits = out
        cells = [list(map(int, bits[i:i+6])) for i in range(0, len(bits), 6)]
        json.dump(cells, sys.stdout, ensure_ascii=False)
    else:
        print(out)

def cmd_to_text(args, tr: BrailleTranslator):
    raw = args.braille or sys.stdin.read().rstrip("\n")
    if args.format == "binary":
        # 파일로 받은 경우
        try:
            cells = json.load(open(raw, encoding="utf-8"))
        except (ValueError, FileNotFoundError):
            # 아니면 문자열 그대로 bits 스트링으로 간주
            bits = raw
            cells = [list(map(int, bits[i:i+6])) for i in range(0, len(bits), 6)]
        restored, = tr.braille_to_text(cells, fmt="binary")
    else:
        restored, = tr.braille_to_text(raw, fmt="unicode")
    print(restored)

def cmd_to_image(args, tr: BrailleTranslator):
    img = tr.text_to_braille_image(args.text)
    cv2.imwrite(args.output, img)
    print(f"Saved braille image to {args.output}")

def cmd_from_image(args, tr: BrailleTranslator):
    img = cv2.imread(args.input)
    cells = tr.image_to_binary(img, cell_size=args.cell_size, margin=args.margin)
    restored, = tr.braille_to_text(cells, fmt="binary")
    print(restored)

def main():
    parser = argparse.ArgumentParser(
        description="Example CLI for BrailleTranslator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("to-braille", help="텍스트 → 점자")
    p.add_argument("text", nargs="?", help="원본 텍스트 (없으면 stdin)")
    p.add_argument("-f", "--format",
                   choices=["unicode", "dots", "binary"],
                   default="unicode",
                   help="출력 포맷 (기본: unicode)")
    p.set_defaults(func=cmd_to_braille)

    p = sub.add_parser("to-text", help="점자 → 텍스트 복원")
    p.add_argument("braille", nargs="?", help="Braille unicode 문자열 또는 binary JSON 파일")
    p.add_argument("-f", "--format",
                   choices=["unicode", "binary"],
                   default="unicode",
                   help="입력 포맷 (기본: unicode)")
    p.set_defaults(func=cmd_to_text)

    p = sub.add_parser("to-image", help="텍스트 → 점자 이미지")
    p.add_argument("text", help="원본 텍스트")
    p.add_argument("-o", "--output",
                   default="braille.png",
                   help="저장할 이미지 파일 (기본: braille.png)")
    p.set_defaults(func=cmd_to_image)

    p = sub.add_parser("from-image", help="점자 이미지 → 텍스트 복원")
    p.add_argument("input", help="점자 이미지 파일 경로")
    p.add_argument("-c", "--cell-size", type=int, default=50, help="셀 크기 (픽셀)")
    p.add_argument("-m", "--margin", type=int, default=20, help="셀 간 여백 (픽셀)")
    p.set_defaults(func=cmd_from_image)

    args = parser.parse_args()

    tr = BrailleTranslator()
    try:
        args.func(args, tr)
    finally:
        tr.shutdown()

if __name__ == "__main__":
    main()