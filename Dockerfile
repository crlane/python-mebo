FROM python:3.7

ADD . /opt/src/
WORKDIR /opt/src
RUN pip install -U pip
RUN pip install .
