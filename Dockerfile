FROM python:3.13-slim

WORKDIR /app
COPY src ./src
ENV PYTHONPATH=/app/src

EXPOSE 8765
CMD ["python", "-m", "howo_capture", "serve", "--host", "0.0.0.0", "--port", "8765"]
