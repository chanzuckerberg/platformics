FROM python:3.11-slim-bookworm AS build

COPY dist/platformics-0.1.0-py3-none-any.whl /tmp/platformics-0.1.0-py3-none-any.whl
RUN cd /tmp/ && pip install platformics-0.1.0-py3-none-any.whl && rm -rf /tmp/*.whl

RUN mkdir -p /app
WORKDIR /app

#CMD ["/usr/local/bin/supervisord", "-c", "/app/etc/supervisord.conf"]
entrypoint ["platformics"]
