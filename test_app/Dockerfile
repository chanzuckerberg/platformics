FROM ghcr.io/chanzuckerberg/platformics:latest

RUN apt update && \
    apt install -y nginx nginx-extras && \
    apt clean

# Some base python dependencies to kickstart our container build.
ENV POETRY_VERSION=1.8
RUN python3 -m pip install --no-cache-dir poetry==$POETRY_VERSION supervisor

# Install dev deps
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock ./
RUN poetry install

RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml .
COPY . .

ENTRYPOINT []
CMD ["/usr/local/bin/supervisord", "-c", "/app/etc/supervisord.conf"]
