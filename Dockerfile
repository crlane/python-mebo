FROM python:3.12.2

ADD . /opt/src/
WORKDIR /opt/src
RUN pip install -U pip
RUN pip install .
