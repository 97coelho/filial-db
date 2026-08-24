FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
ENV FLASK_APP=wsgi:app FILIAL_BSB_DATA_DIR=/var/lib/filial-bsb
EXPOSE 5000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--workers=1", "--access-logfile=-", "--error-logfile=-", "wsgi:app"]
