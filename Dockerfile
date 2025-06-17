# ┌────────────────────────────┐
# │ 1) Builder Stage           │
# └────────────────────────────┘
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# 시스템 의존성
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3-pip \
        liblouis-bin \
        liblouis-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 소스 복사
COPY . /app

# 가상환경 생성 및 의존성 설치
RUN python3.11 -m venv .venv \
    && . .venv/bin/activate \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# 점자 테이블 동기화 스크립트 실행
RUN chmod +x scripts/import_all_tables.sh \
    && . .venv/bin/activate \
    && scripts/import_all_tables.sh

# 테스트 실행
RUN . .venv/bin/activate \
    && pytest --maxfail=1 --disable-warnings -q

# ┌────────────────────────────┐
# │ 2) Runtime Stage           │
# └────────────────────────────┘
FROM ubuntu:22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

# 런타임에만 필요한 패키지
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
        liblouis-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# builder에서 준비된 가상환경, 소스, 테이블, bin 디렉터리 복사
COPY --from=builder /app/.venv       /app/.venv
COPY --from=builder /app/braille_translator /app/braille_translator
COPY --from=builder /app/bin         /app/bin
COPY --from=builder /app/tables      /app/tables
COPY --from=builder /app/translator.py   /app/translator.py
COPY --from=builder /app/main.py     /app/main.py
COPY --from=builder /app/requirements.txt /app/requirements.txt

# CLI 진입점
ENTRYPOINT ["bash", "-lc"]
CMD ["python main.py"]