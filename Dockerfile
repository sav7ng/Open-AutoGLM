# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       g++ \
       libc6-dev \
       libffi-dev \
       libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

FROM python:3.11-slim AS runtime

WORKDIR /app

# Bookworm mirrors (align with python:3.11-slim base)
RUN echo "deb http://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
    && echo "deb http://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.ustc.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends -o Acquire::Retries=3 \
       curl \
       android-tools-adb \
       iputils-ping \
       openssh-client \
       autossh \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ADB client authentication (pair with devices / adb server as usual)
RUN mkdir -p /root/.android
COPY adbkey/adbkey /root/.android/adbkey
RUN chmod 600 /root/.android/adbkey

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY phone_agent/ ./phone_agent/
COPY app/ ./app/
COPY server.py .

# ssh_tunnel: container must reach params.ssh_host:ssh_port; direct needs TCP to params.address
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/openapi.json > /dev/null || exit 1

CMD ["python", "server.py"]
