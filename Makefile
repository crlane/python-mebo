ORG ?= crlane
IMAGE ?= python-mebo
TEST_IMAGE ?= ${IMAGE}-test
BUILD_IMAGE ?= ${IMAGE}-build
DEV_IMAGE ?= ${IMAGE}-dev

VERSION_FILE ?= ./mebo/__init__.py
VERSION ?= $(shell grep -E -o '\d+.\d+.\d+(.dev\d+)?' ${VERSION_FILE})

.PHONY: image publish build _test_image test run publish

all: image test

base:
	@docker build -t ${ORG}/${IMAGE} .

build: base 
	@docker build -t ${ORG}/${BUILD_IMAGE} . -f Dockerfile-build

_dev_image: base
	@docker build -t ${ORG}/${DEV_IMAGE} . -f Dockerfile-dev
	
_test_image: base
	@docker build -t ${ORG}/${TEST_IMAGE} . -f Dockerfile-test

test: _test_image
	@docker run --rm -it -e PYTHONDONTWRITEBYTECODE=1 -v`pwd`:/opt/src ${ORG}/${TEST_IMAGE}

dev: _dev_image
	@docker run --rm -it ${ORG}/${DEV_IMAGE}

run:
	@docker run --rm -it --net host ${ORG}/${IMAGE} bash

# deploy to PyPI, tag the version, and push to dockerhub
publish: 
	@docker run --rm -e PYPI_PASSWORD=${PYPI_PASSWORD} -e PYPI_USER=${PYPI_USER} ${ORG}/${BUILD_IMAGE}
	@docker tag ${ORG}/${IMAGE} ${ORG}/${IMAGE}:${VERSION}
	@docker push ${ORG}/${IMAGE}:${VERSION}
