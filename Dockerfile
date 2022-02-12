# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

WORKDIR /app
VOLUME /rec

COPY src src/
COPY setup.py setup.cfg .

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir -e . \
    && apt-get purge -y --auto-remove build-essential python3-dev
# ref: https://github.com/docker-library/python/issues/60#issuecomment-134322383

ENTRYPOINT ["blrec", "-o", "/rec", "--host", "0.0.0.0"]
CMD ["-c", "/rec/settings.toml"]
