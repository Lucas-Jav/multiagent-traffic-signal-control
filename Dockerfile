FROM ghcr.io/eclipse-sumo/sumo:v1_27_1

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/

ARG PYTHON_VERSION=3.12.11

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    ARTIFACTS_DIR=/app/artifacts

WORKDIR /app

RUN uv python install "${PYTHON_VERSION}" \
    && sumo --version

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --python "${PYTHON_VERSION}" --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --python "${PYTHON_VERSION}" --no-dev --no-editable \
    && test "$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')" = "3.12" \
    && python -c "import traci, sumolib"

COPY scripts ./scripts
COPY scenarios ./scenarios
COPY docs ./docs
COPY experiments ./experiments

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/artifacts \
    && chown -R app:app /app/artifacts \
    && rm -f /usr/local/bin/uv /usr/local/bin/uvx

USER app

CMD ["traffic-agents"]
