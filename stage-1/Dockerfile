FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home service
WORKDIR /app
COPY errors.py json_value.py local_time.py state.py service.py server.py ./
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080
USER 10001
EXPOSE 8080
CMD ["python", "server.py"]
