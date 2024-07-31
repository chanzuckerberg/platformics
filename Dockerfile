FROM python:3.12-slim-bookworm AS build

RUN apt update && \
    apt install -y make gcc git && \
    apt clean

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY dist /tmp/dist
RUN cd /tmp/dist && pip install *.whl && rm -rf /tmp/*.whl

RUN mkdir -p /app
WORKDIR /app

ENTRYPOINT ["platformics"]
