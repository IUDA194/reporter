FROM python:3.13-slim-alpine

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

ADD . /app
WORKDIR /app
COPY . .

RUN uv sync --locked --no-dev

CMD ["uv", "run", "main.py"]