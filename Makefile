ORG ?= crlane
IMAGE ?= python-mebo
TEST_IMAGE ?= ${IMAGE}-test
BUILD_IMAGE ?= ${IMAGE}-build

.PHONY: image publish build _test_image test run publish

all: image test

image:
	@docker build -t ${ORG}/${IMAGE} .

build: image
	docker build -t ${ORG}/${BUILD_IMAGE} . -f Dockerfile-build

_test_image:
	@docker build -t ${ORG}/${TEST_IMAGE} . -f Dockerfile-test

test: _test_image
	@docker run --rm -it -e PYTHONDONTWRITEBYTECODE=1 -v`pwd`:/opt/src ${ORG}/${TEST_IMAGE}

run:
	@docker run --rm -it ${ORG}/${IMAGE} bash

publish:
	@docker run --rm -e PYPI_PASSWORD=${PYPI_PASSWORD} -e PYPI_USER=${PYPI_USER} ${ORG}/${BUILD_IMAGE}
