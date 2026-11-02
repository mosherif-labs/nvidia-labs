# Build from the repo root: docker build -f app/service/Dockerfile .
FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "redis>=5" langgraph langgraph-checkpoint-postgres \
    langgraph-checkpoint-sqlite "psycopg[binary]" langchain-openai openai pydantic
COPY app /srv/app
WORKDIR /srv/app/service
# /srv on the path so `from app.team.team import g` resolves, like the editable install does locally
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/srv
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
