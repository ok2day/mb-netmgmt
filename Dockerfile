FROM node:16-alpine
RUN npm install -g mountebank
ENTRYPOINT ["mb"]
RUN apk add \
    git \
    py3-lxml \
    py3-paramiko \
    py3-pip \
    py3-requests \
    gcc \
    musl-dev \
    python3-dev
RUN pip install scapy@git+https://github.com/secdev/scapy
COPY ./ /var/tmp/mb-netmgmt
RUN pip install -e /var/tmp/mb-netmgmt
WORKDIR /var/tmp/mb-netmgmt/mb_netmgmt
