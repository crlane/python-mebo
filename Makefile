ORG ?= crlane
IMAGE ?= python-mebo
TEST_IMAGE ?= ${IMAGE}-test
BUILD_IMAGE ?= ${IMAGE}-build
DEV_IMAGE ?= ${IMAGE}-dev

.PHONY: image publish build _test_image test run publish

all: image test

image:
	@docker build -t ${ORG}/${IMAGE} .

build: image
	docker build -t ${ORG}/${BUILD_IMAGE} . -f Dockerfile-build

_dev_image: image
	@docker build -t ${ORG}/${DEV_IMAGE} . -f Dockerfile-dev
	
_test_image: image
	@docker build -t ${ORG}/${TEST_IMAGE} . -f Dockerfile-test

test: _test_image
	@docker run --rm -it -e PYTHONDONTWRITEBYTECODE=1 -v`pwd`:/opt/src ${ORG}/${TEST_IMAGE}

dev: _dev_image
	@docker run --rm -it ${ORG}/${DEV_IMAGE}

run:
	@docker run --rm -it --net host ${ORG}/${IMAGE} bash

publish: image
	@docker run --rm -e PYPI_PASSWORD=${PYPI_PASSWORD} -e PYPI_USER=${PYPI_USER} ${ORG}/${BUILD_IMAGE}
