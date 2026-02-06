FROM ghcr.io/osgeo/gdal:ubuntu-small-3.12.0 AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV GML_SKIP_CORRUPTED_FEATURES=YES
ENV BUILD_DIR=/usr/local
ENV MHUB_DIR=$BUILD_DIR/src/mapchete_hub
# Set environment variables for uv and Python
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR $MHUB_DIR

COPY pyproject.toml uv.lock $MHUB_DIR/

# copy mapchete_hub source code and install
COPY . $MHUB_DIR

# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --locked --no-install-project --no-dev
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev

FROM ghcr.io/osgeo/gdal:ubuntu-small-3.12.0 AS runner
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV BUILD_DIR=/usr/local
ENV MHUB_DIR=$BUILD_DIR/src/mapchete_hub

COPY --from=builder /$MHUB_DIR /$MHUB_DIR
ENV PATH="/${MHUB_DIR}/.venv/bin:${PATH}"
