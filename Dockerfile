FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/hf \
    MPLCONFIGDIR=/tmp/mpl

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy full repo (root is the build context)
COPY . .

# use existing pyproject.toml for editable install
RUN python -m pip install --upgrade pip && pip install -e .

# optional: preload models
RUN python -c "from marker.models import load_all_models; load_all_models()"

EXPOSE 8080
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]
