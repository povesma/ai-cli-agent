FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install pytest

COPY *agent.py .
# Test the syntax of the python files
RUN mypy *.py

# Run the tests
RUN mypy *.py
# Environment variables are provided in runtime like: docker run --env-file .env
ENV GPT_API_URL=
ENV GPT_SUBSCRIPTION_KEY=
ENV GPT_TOKEN=
ENV GPT_MODEL=CLAUDE_3_SONNET_35

CMD ["python", "agent.py"]
