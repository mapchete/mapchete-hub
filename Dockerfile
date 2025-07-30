FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.3 AS runner

ENV GML_SKIP_CORRUPTED_FEATURES=YES
ENV BUILD_DIR=/usr/local
ENV MHUB_DIR=$BUILD_DIR/src/mapchete_hub
ENV UV_NO_CACHE=true

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN ls

COPY requirements.in $MHUB_DIR/
RUN uv venv
RUN uv pip install -r $MHUB_DIR/requirements.in

# copy mapchete_hub source code and install
COPY . $MHUB_DIR

RUN uv pip install --editable $MHUB_DIR/

WORKDIR $MHUB_DIR
