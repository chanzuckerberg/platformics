FROM python:3.12-slim-bookworm AS build

RUN apt update && \
    apt install -y make gcc && \
    apt clean

COPY dist/platformics-0.1.0-py3-none-any.whl /tmp/platformics-0.1.0-py3-none-any.whl
RUN cd /tmp/ && pip install platformics-0.1.0-py3-none-any.whl && rm -rf /tmp/*.whl

RUN mkdir -p /app
WORKDIR /app

ENTRYPOINT ["platformics"]
