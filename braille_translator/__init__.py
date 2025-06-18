# -*- coding: utf-8 -*-

"""
braille-translator 패키지
이 파일을 통해 외부에서 패키지의 주요 클래스에 쉽게 접근할 수 있습니다.
V5 엔진을 기본으로 공개합니다.
"""

# 패키지 버전
__version__ = "0.5.0"

# v5 모듈에서 필요한 모든 클래스와 타입을 가져옵니다.
from .translator_v5 import (
    SuperBrailleTranslator,
    InputFormatDetector,
    LanguageDetector,
    LanguageType,
    ContractionLevel,
    UnifiedTranslationResult,
    HAS_IMAGE_SUPPORT
)

# 이 패키지를 import 했을 때, 외부로 공개할 API 목록을 정의합니다.
__all__ = [
    "SuperBrailleTranslator",
    "InputFormatDetector",
    "LanguageDetector",
    "LanguageType",
    "ContractionLevel",
    "UnifiedTranslationResult",
    "HAS_IMAGE_SUPPORT"
]

# 이 패키지를 import 했을 때, 외부로 공개할 API 목록을 정의합니다.
__all__ = [
    "SuperBrailleTranslator",
    "InputFormatDetector",
    "LanguageDetector",
    "LanguageType",
    "ContractionLevel",
    "UnifiedTranslationResult",
    "HAS_IMAGE_SUPPORT"
]

# # 패키지 버전
# __version__ = "0.1.0"

# # 실제로 존재하는 것만 import
# from .translator_v1 import (
#     BrailleTranslator,
#     unicode_to_dots,
#     unicode_to_binary,
#     binary_to_unicode,
# )

# # 공개 API
# __all__ = [
#     "BrailleTranslator",
#     "unicode_to_dots",
#     "unicode_to_binary",
#     "binary_to_unicode",
# ]