# Build from the repo root: docker build -f app/service/Dockerfile .
FROM python:3.12-slim
WORKDIR /srv
COPY app/team/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt fastapi "uvicorn[standard]" "redis>=5" \
    langgraph-checkpoint-postgres "psycopg[binary]"
COPY labs/rag /srv/labs/rag
COPY app /srv/app
WORKDIR /srv/app/service
# /srv on the path so `from app.team.team import g` resolves, like the editable install does locally
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/srv
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
