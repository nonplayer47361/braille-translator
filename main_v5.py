# -*- coding: utf-8 -*-
"""
【 통합 점자 번역 시스템 V5 - Command Line Interface 】
braille_translator 엔진의 모든 기능을 활용하는 사용자 친화적 인터페이스
"""

import os
import sys
import logging
from datetime import datetime

# main.py가 braille_translator 폴더를 찾을 수 있도록 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# translator_v5 모듈에서 필요한 클래스들을 가져옵니다.
from braille_translator.translator_v5 import SuperBrailleTranslator, UnifiedTranslationResult, HAS_IMAGE_SUPPORT

# 이미지 라이브러리가 없는 경우를 대비하여 cv2를 선택적으로 임포트
if HAS_IMAGE_SUPPORT:
    import cv2

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def print_translation_result(result: UnifiedTranslationResult):
    """상세 번역 결과를 포맷에 맞게 예쁘게 출력하는 함수"""
    if not result or not result.success:
        print(f"\n[오류] 번역에 실패했습니다: {result.error_message if result else '알 수 없는 오류'}")
        return

    print("\n" + "="*25 + " 번역 결과 " + "="*25)
    display_data = result.to_display_dict()
    for key, value in display_data.items():
        print(f"  - {key}: {value}")
    
    print("\n  --- 상세 분석 (언어별 세그먼트) ---")
    if result.segments:
        for seg_text, seg_lang in result.segments:
            print(f"    - '{seg_text}' [{seg_lang}]")
    else:
        print("    - 상세 분석 정보가 없습니다.")
    print("="*62)


def main_cli():
    """메인 CLI 함수"""
    # 번역기 엔진 초기화
    translator = SuperBrailleTranslator(table_dir="tables")
    
    print("\n" + "="*50)
    print(" V5 점자 번역 시스템 (통합 CLI)")
    print("="*50)

    while True:
        print("\n--- 메뉴 ---")
        print("1. 텍스트에서 점자 생성 (모든 포맷 및 이미지)")
        print("2. 점자/이미지에서 텍스트 복원")
        print("3. 번역 통계 보기")
        print("4. 종료")

        choice = input("\n선택하세요 (1-4): ").strip()

        if choice == '1':
            text = input("번역할 텍스트를 입력하세요: ").strip()
            if text:
                generate_image = True
                if not HAS_IMAGE_SUPPORT:
                    print("\n[알림] 이미지 라이브러리가 없어 이미지는 생성되지 않습니다.")
                    generate_image = False
                else:
                    img_choice = input("점자 이미지를 함께 생성하시겠습니까? (Y/n): ").strip().lower()
                    if img_choice == 'n':
                        generate_image = False

                result = translator.unified_translate(text, generate_image=generate_image)
                print_translation_result(result)

        elif choice == '2':
            user_input = input("복원할 점자(유니코드/점번호/이진수) 또는 이미지 파일 경로를 입력하세요: ").strip()
            if not user_input: continue

            restored_text, detected_type = translator.unified_restore(user_input)
            
            print(f"\n--- 복원 결과 (감지된 타입: {detected_type}) ---")
            if "[복원 실패" in restored_text:
                print(f"[오류] {restored_text}")
            else:
                print(f"  - 입력: {user_input[:70]}" + ("..." if len(user_input) > 70 else ""))
                print(f"  - 텍스트: {restored_text}")
            print("-" * 20)

        elif choice == '3':
            stats = translator.get_statistics()
            print("\n--- 번역 통계 ---")
            for key, value in stats.items():
                if "rate" in key:
                    print(f"  - {key}: {value:.2f}%")
                else:
                    print(f"  - {key}: {value}")
            print("-" * 20)

        elif choice == '4':
            print("프로그램을 종료합니다.")
            break
        
        else:
            print("잘못된 선택입니다. 다시 입력해주세요.")

if __name__ == "__main__":
    try:
        main_cli()
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")