# HOMEPEDIA - FastAPI backend (DEV image)
# Built from repo root: context = repo root, so paths are repo-relative.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# System deps for psycopg2 build are avoided by using psycopg2-binary.
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

# Source is bind-mounted in dev for hot reload (see docker-compose volumes),
# but we copy it too so the image is runnable standalone.
COPY src ./src

EXPOSE 8000

# --reload enabled for dev ergonomics; drop it in prod image.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
