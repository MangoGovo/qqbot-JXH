# ===== 构建阶段 =====
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先安装依赖（缓存友好）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# 拷贝源码
ADD . /app

# 安装项目（包含自身）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable


# ===== 运行阶段 =====
FROM python:3.12-slim

WORKDIR /app

# 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制源码（运行时需要）
COPY --from=builder /app /app

# 设置 PATH，使用虚拟环境里的 python
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 运行入口
CMD ["python", "main.py"]
