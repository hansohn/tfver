ARG DEBIAN_VERSION=stable-slim

# debian
FROM debian:${DEBIAN_VERSION}
ARG PYTHON_VERSION=3.9
ENV CURL='curl -fsSL --netrc-optional'
RUN apt-get update && apt-get install --no-install-recommends -y \
      bash \
      jq \
      software-properties-common \
      tar \
      vim \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get install --no-install-recommends -y \
      python${PYTHON_VERSION} \
      python3-pip
COPY dist/. /root/
RUN /bin/bash -c 'pip install /root/tfrelease-*.tar.gz'
