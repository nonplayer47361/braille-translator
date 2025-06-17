# Cross-Platform Braille Translator

**Python** + **liblouis** (`lou_translate` CLI) 기반의  
영어·한글·숫자·특수문자 혼합 텍스트 ↔ 점자 변환·복원 도구입니다.

- Grade 2 → Grade 1 폴백  
- Unicode Braille, 점번호 리스트, 6비트 이진 배열 출력  
- OpenCV 기반 점자 이미지 생성 및 이미지→이진화→복원  

---

## 🔧 주요 기능

1. **Text → Braille**  
   - `unicode` (⠠⠓⠑…)  
   - `dots` (점번호 `[1,2,5,…]`)  
   - `binary` (6비트 배열 `[1,0,1,0,0,1]`)  

2. **Braille → Text**  
   - Unicode Braille → 원문  
   - 6비트 이진 배열(JSON) → 원문  

3. **Text → Image**  
   - OpenCV로 점자 셀 그리기  

4. **Image → Binary → Text**  
   - 점자 이미지에서 셀별 이진 배열을 추출 후 복원  

---

## 📂 프로젝트 구조
project-root/
├── bin/                         # OS별 lou_translate 바이너리
│   ├── macos/lou_translate
│   ├── linux/lou_translate
│   └── windows/lou_translate.exe
├── liblouis-src/               # liblouis 소스 전체 (tables/, docs/…)
├── tables/                     # liblouis 모든 .ctb/.dis 테이블
├── scripts/
│   └── import_all_tables.sh    # tables/ 동기화 스크립트
├── braille_translator/         # 파이썬 패키지 (엔진 모듈)
│   └── translator.py           # BrailleTranslator 클래스
├── translator.py               # CLI 진입점 (argparse 기반)
├── main.py                     # 터미널 상호작용용 인터페이스
├── examples/
│   └── example_usage.py        # 사용 예시
├── tests/
│   ├── conftest.py             # pytest 설정
│   └── test_translator.py      # 유닛 테스트
├── requirements.txt            # Python 의존성
└── .gitignore
---

## 🚀 설치


# 1) 가상환경 생성 & 활성화
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate

# 2) Python 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 3) 테이블 동기화
chmod +x scripts/import_all_tables.sh
./scripts/import_all_tables.sh

# 4) lou_translate 준비
# └── bin/ 아래에 OS별 바이너리 복사 & 실행 권한 부여
chmod +x bin/macos/lou_translate bin/linux/lou_translate
# Windows: lou_translate.exe를 bin/windows/에 복사
-
---
🎯 사용 예시

1. **Python API**
from braille_translator.translator import BrailleTranslator

tr = BrailleTranslator()

text = "Hello 안녕 123! @#"
# 유니코드 점자
print(tr.text_to_braille(text, fmt="unicode"))

# 점번호 리스트
print(tr.text_to_braille(text, fmt="dots"))

# 이진 배열(JSON)
print(tr.text_to_braille(text, fmt="binary"))

# 복원 (Unicode Braille → Text)
b_uni = tr.text_to_braille(text, fmt="unicode")
print(tr.braille_to_text(b_uni, fmt="unicode"))

# 이미지 생성 & 복원
img = tr.text_to_braille_image(text)
# cv2.imwrite("out.png", img)

bins = tr.image_to_binary(img)
print(tr.braille_to_text(bins, fmt="binary"))

2. **CLI**
# 텍스트 → 유니코드 점자
python translator.py text2braille -f unicode -i "Hello 안녕"

# 유니코드 점자 → 텍스트 복원
python translator.py braille2text -f unicode -i "⠠⠓⠑⠇⠇⠕"

# 텍스트 → 점자 이미지
python translator.py text2image -i "안녕하세요" -o braille.png

# 이미지 → 이진 배열(JSON)
python translator.py image2binary -i braille.png --cell-size 60 --margin 15 > cells.json
---
✅ 테스트
pip install pytest
pytest --maxfail=1 -q
# → 로그는 tests/logs/test_results.log에 기록됩니다.
---
🛠️ 기여 및 확장
•	다국어 테이블 추가: tables/<lang>/…
•	PyPI 배포, Docker 이미지 제작
•	CI/CD: GitHub Actions 워크플로우 등
---
📜 라이선스
iblouis: LGPL
