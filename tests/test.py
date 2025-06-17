import subprocess

def text_to_braille(text: str) -> str:
    """
    텍스트를 liblouis CLI로 점자 Unicode로 변환합니다.
    liblouis가 설치된 환경에서만 동작합니다.
    """
    # - display table(unicode.dis)과 translation table(en-us-g2.ctb)를 콤마로 연결
    table_arg = "unicode.dis,en-us-g2.ctb"
    result = subprocess.run(
        ["lou_translate", table_arg],
        input=text,
        text=True,
        capture_output=True,
        check=True
    )
    return result.stdout

if __name__ == "__main__":
    sample = "hi"
    braille = text_to_braille(sample)
    print(braille)  # ⠠⠓⠑⠇⠇⠕