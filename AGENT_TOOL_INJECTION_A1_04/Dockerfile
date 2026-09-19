# ToolGuard evaluation image: project code plus a CPU-only Ollama runtime.
#
# The model is deliberately NOT baked in. A 4-bit 7B model is 4.7 GB, which
# would make the image an awkward object to build, store, and move around. It
# is mounted at /models instead; the entrypoint pulls it if that mount is
# empty, so a fresh machine still needs nothing but `docker compose run`.

# ---------------------------------------------------------------------------
# Stage 1: fetch Ollama.
#
# The project-local install under .local/ollama is an Arch package whose
# llama-server runners link against glibc 2.43, so they cannot run on a Debian
# base image. The official release tarball is built against a much older glibc
# and is portable. The version is pinned to the one used for the recorded
# results. Only the CPU runners are kept; the CUDA and ROCm directories are
# several hundred MB of dead weight for this CPU-only experiment.
# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS ollama

ARG OLLAMA_VERSION=0.32.15
ARG OLLAMA_URL=https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates zstd \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/ollama /tmp/dl \
 && curl -fsSL "${OLLAMA_URL}" -o /tmp/dl/ollama.tar.zst \
 && tar --zstd -xf /tmp/dl/ollama.tar.zst -C /opt/ollama \
      --exclude='*cuda*' --exclude='*rocm*' --exclude='*mlx*' \
 && rm -rf /tmp/dl \
 && /opt/ollama/bin/ollama --version || true

# ---------------------------------------------------------------------------
# Stage 2: the evaluation image.
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# curl backs the entrypoint's readiness probe; nothing else needs the network.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ollama /opt/ollama/bin/ollama /opt/ollama/bin/ollama
COPY --from=ollama /opt/ollama/lib/ollama /opt/ollama/lib/ollama

# A real account for uid 1000, so an interactive `shell` shows a normal prompt
# instead of bash's "I have no name!" fallback for an unresolvable uid.
#
# Ollama writes a keypair to $HOME/.ollama on startup. The home directory is
# world-writable so the container still works when `user:` is overridden to a
# uid other than 1000; nothing of value is kept there.
RUN groupadd --gid 1000 toolguard \
 && useradd --uid 1000 --gid 1000 --home-dir /home/toolguard --shell /bin/bash toolguard \
 && mkdir -p /home/toolguard && chmod 0777 /home/toolguard

ENV HOME=/home/toolguard \
    PATH="/opt/ollama/bin:${PATH}" \
    OLLAMA_MODELS=/models \
    OLLAMA_HOST=127.0.0.1:11434 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY config.yaml ./
COPY src ./src
COPY experiments ./experiments
COPY data ./data
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

# Runs as an unprivileged user so logs written to the host bind mount are owned
# by the invoking user, not root. data/ is writable because every trial resets
# the mock workspace in place.
RUN chmod +x /usr/local/bin/entrypoint.sh \
 && mkdir -p /app/logs /models \
 && chown -R 1000:1000 /app /models
USER 1000:1000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["suite"]
