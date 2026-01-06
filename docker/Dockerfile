FROM python:3.12

# Variables de base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    pcsc-tools \
    libpcsclite1 \
    libpcsclite-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installation des libs Python nécessaires
RUN pip install --upgrade pip && \
    pip install \
        flask \
        pyscard \
        click \
        mysql-connector-python \
        bcrypt

# Dossier applicatif
WORKDIR /app

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
