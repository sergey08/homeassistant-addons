ARG BUILD_FROM=python:3.13-alpine
FROM $BUILD_FROM
WORKDIR /app
RUN pip install --no-cache-dir flask==3.1.1 Markdown==3.8.2 gunicorn==23.0.0
COPY server.py /app/server.py
EXPOSE 8099
CMD ["gunicorn", "--bind", "0.0.0.0:8099", "--workers", "2", "--access-logfile", "-", "server:app"]
