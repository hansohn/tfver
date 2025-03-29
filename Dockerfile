ARG PYTHON_VERSION=3.12

# python
FROM python:${PYTHON_VERSION} AS main
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --no-install-recommends -y \
      bash \
      gpg-agent \
      jq \
      software-properties-common \
      tar \
      vim
WORKDIR /app
COPY dist/. .
RUN /bin/bash -c 'python${PYTHON_VERSION%%.*} -m pip install /app/tfver-*.tar.gz'
