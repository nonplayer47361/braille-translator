# -*- coding: utf-8 -*-
"""
【 통합 점자 번역 시스템 V5 - Command Line Interface 】
braille_translator 엔진의 모든 기능을 활용하는 사용자 친화적 인터페이스
"""

import os
import sys
import logging
from datetime import datetime

# main_v5.py가 braille_translator 폴더를 찾을 수 있도록 경로 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# translator_v5 모듈에서 필요한 클래스들을 가져옵니다.
from braille_translator.translator_v5 import SuperBrailleTranslator, UnifiedTranslationResult, HAS_IMAGE_SUPPORT

# 이미지 라이브러리가 없는 경우를 대비하여 cv2를 선택적으로 임포트
if HAS_IMAGE_SUPPORT:
    import cv2

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# 【수정】 main_v5.py를 위한 logger 객체 생성
logger = logging.getLogger(__name__)


def print_translation_result(result: UnifiedTranslationResult):
    """상세 번역 결과를 포맷에 맞게 예쁘게 출력하는 함수"""
    if not result or not result.success:
        print(f"\n[오류] 번역에 실패했습니다: {result.error_message if result else '알 수 없는 오류'}")
        return

    print("\n" + "="*80)
    print("✨ 번역 결과 - 모든 포맷")
    print("="*80)

    display_dict = result.to_display_dict()
    for key, value in display_dict.items():
        icon = "📋"
        if "이미지" in key: icon = "🖼️ "
        elif "유니코드" in key: icon = "⠿ "
        elif "점번호" in key or "이진" in key: icon = "🔢"
        print(f"{icon} {key}: {value}")

    print(f"\n🌐 언어별 세그먼트 분석:")
    if result.segments:
        for i, (seg_text, seg_lang) in enumerate(result.segments, 1):
            print(f"   {i}. '{seg_text}' → {seg_lang}")
    else:
        print("   - 분석 정보가 없습니다.")
    print("="*80)


def main_cli():
    """메인 CLI 함수"""
    translator = SuperBrailleTranslator(table_dir="tables")
    
    print("\n" + "="*80)
    print("🔥 통합 점자 번역 시스템 V5 🔥")
    print("번역-이미지-복원 완전 통합 | 모든 포맷 자동 지원")
    print("="*80)

    while True:
        print("\n" + "="*50)
        print("📋 메뉴")
        print("="*50)
        print("1. 📝 텍스트 번역 (→ 모든 점자 포맷 + 이미지)")
        print("2. 🔄 점자 복원 (모든 포맷 자동 감지 → 텍스트)")
        print("3. 📊 시스템 통계")
        print("4. 🚪 종료")
        
        choice = input("\n선택하세요 (1-4): ").strip()

        if choice == '1':
            # ... (이전과 동일)
            pass

        elif choice == '2':
            # ... (이전과 동일)
            pass

        elif choice == '3':
            # ... (이전과 동일)
            pass

        elif choice == '4':
            print("\n👋 프로그램을 종료합니다.")
            print("감사합니다! 🙏")
            break
        
        else:
            print("❌ 잘못된 선택입니다. 1-4 중에서 선택해주세요.")


if __name__ == "__main__":
    try:
        main_cli()
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 프로그램을 종료했습니다.")
    except Exception as e:
        # 【수정】 이제 logger 객체가 정의되었으므로 정상적으로 오류를 기록합니다.
        logger.error(f"시스템 오류: {e}", exc_info=True)
        print(f"💥 시스템 오류가 발생했습니다: {e}")