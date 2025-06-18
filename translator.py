#!/usr/bin/env python3
# File: translator.py
# 설명: 터미널 인자 기반 점자 변환/복원 CLI
#
# 사용 예제:
#   # 텍스트 → 유니코드 점자
#   python translator.py text2braille -f unicode -i "Hello 안녕"
#
#   # 텍스트 → 점번호
#   python translator.py text2braille -f dots -i "123!"
#
#   # 텍스트 → 이진 배열 (JSON)
#   python translator.py text2braille -f binary -i "Test" > cells.json
#
#   # 유니코드 점자 → 텍스트 복원
#   python translator.py braille2text -f unicode -i "⠠⠓⠑⠇⠇⠕"
#
#   # JSON 바이너리 → 텍스트 복원
#   python translator.py braille2text -f binary -i cells.json
#
#   # 텍스트 → 점자 이미지 저장
#   python translator.py text2image -i "안녕하세요" -c 60 -m 15 -r 10
#
#   # 이미지 → 이진 배열 (JSON)
#   python translator.py image2binary -i out.png -c 60 -m 15

import argparse
import sys
import json
import os
import datetime

import cv2

from braille_translator.translator_v1 import BrailleTranslator

def unicode_to_dots(uni: str) -> str:
    """
    유니코드 점자 문자열을 '123,145,...' 형태의 점번호 문자열로 변환
    """
    dots_list = []
    for ch in uni:
        code = ord(ch) - 0x2800
        nums = [str(i+1) for i in range(6) if (code >> i) & 1]
        dots_list.append(''.join(nums) or '0')
    return ' '.join(dots_list)

def unicode_to_binary(uni: str) -> str:
    """
    유니코드 점자 문자열을 '010101...' 형태의 비트 문자열로 변환
    """
    return ''.join(f"{ord(ch) - 0x2800:06b}" for ch in uni)

def main():
    parser = argparse.ArgumentParser(
        prog="translator",
        description="텍스트↔점자 변환 및 복원 도구"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # 1) text2braille
    p = sub.add_parser("text2braille", help="텍스트를 점자로 변환")
    p.add_argument("-f","--format", choices=["unicode","dots","binary"],
                   default="unicode", help="출력 포맷 (기본: unicode)")
    p.add_argument("-i","--input", help="변환할 텍스트 (없으면 stdin)")

    # 2) braille2text
    p = sub.add_parser("braille2text", help="점자를 텍스트로 복원")
    p.add_argument("-f","--format", choices=["unicode","binary"],
                   default="unicode", help="입력 포맷 (기본: unicode)")
    p.add_argument("-i","--input",
                   help="유니코드 점자 문자열 또는 JSON 파일 경로 (없으면 stdin)")

    # 3) text2image
    p = sub.add_parser("text2image", help="텍스트를 점자 이미지로 저장하고 메타 기록")
    p.add_argument("-i","--input", required=True, help="이미지로 변환할 텍스트")
    p.add_argument("-c","--cell-size", type=int, default=50,
                   help="셀 크기(px, 기본:50)")
    p.add_argument("-m","--margin", type=int, default=20,
                   help="셀 여백(px, 기본:20)")
    p.add_argument("-r","--radius", type=int, default=8,
                   help="점 반지름(px, 기본:8)")

    # 4) image2binary
    p = sub.add_parser("image2binary", help="점자 이미지에서 이진 배열 추출")
    p.add_argument("-i","--input", required=True, help="이미지 파일 경로")
    p.add_argument("-c","--cell-size", type=int, default=50,
                   help="셀 크기(px, 기본:50)")
    p.add_argument("-m","--margin", type=int, default=20,
                   help="셀 여백(px, 기본:20)")

    args = parser.parse_args()
    tr = BrailleTranslator()

    if args.mode == "text2braille":
        text = args.input or sys.stdin.read().rstrip("\n")
        out = tr.text_to_braille(text, fmt=args.format)
        print(out)

    elif args.mode == "braille2text":
        if args.format == "binary":
            data = args.input or sys.stdin.read().rstrip("\n")
            cells = json.load(open(data, encoding="utf-8"))
            out = tr.braille_to_text(cells, fmt="binary")
        else:
            bri = args.input or sys.stdin.read().rstrip("\n")
            out = tr.braille_to_text(bri, fmt="unicode")
        print(out)

    elif args.mode == "text2image":
        text = args.input
        root = "data"
        os.makedirs(root, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(root, ts)
        os.makedirs(run_dir)

        uni = tr.text_to_braille(text, fmt="unicode")
        dots = unicode_to_dots(uni)
        bin_str = unicode_to_binary(uni)
        bin_chunks = [bin_str[i:i+6] for i in range(0,len(bin_str),6)]

        img = tr.text_to_braille_image(
            text, cell_size=args.cell_size,
            margin=args.margin, dot_radius=args.radius
        )
        img_path = os.path.join(run_dir, "braille.png")
        cv2.imwrite(img_path, img)

        meta = {
            "input_text": text,
            "unicode": uni,
            "dots": dots,
            "binary_chunks": bin_chunks,
            "image_file": "braille.png"
        }
        with open(os.path.join(run_dir, "metadata.json"), "w", encoding="utf-8") as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=2)

        print(f"Run directory: {run_dir}")
        print(f" - Image : {img_path}")
        print(f" - Meta  : metadata.json")

    elif args.mode == "image2binary":
        img = cv2.imread(args.input, cv2.IMREAD_GRAYSCALE)
        cells = tr.image_to_binary(
            img, cell_size=args.cell_size, margin=args.margin
        )
        print(json.dumps(cells, ensure_ascii=False, indent=2))

    else:
        parser.print_help()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()