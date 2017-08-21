ORG ?= crlane
IMAGE ?= python-mebo
TEST_IMAGE ?= ${IMAGE}-test
BUILD_IMAGE ?= ${IMAGE}-build
DEV_IMAGE ?= ${IMAGE}-dev

VERSION_FILE ?= mebo/__init__.py
VERSION ?= $(shell grep -E -o '[0-9]+.[0-9]+.[0-9]+(.dev[0-9]+)?' ${VERSION_FILE})

all: base clean test

.IGNORE: clean

clean:
	@rm -r *.egg-info
	@find . -iname '*.pyc' -delete

.PHONY: version
version:
	@echo ${VERSION}

.PHONY: base
base:
	@docker build -t ${ORG}/${IMAGE} .

.PHONY: _dev_image
_dev_image: base
	@docker build -t ${ORG}/${DEV_IMAGE} . -f Dockerfile-dev
	
.PHONY: _test_image
_test_image: base
	@docker build -t ${ORG}/${TEST_IMAGE} . -f Dockerfile-test

.PHONY: _deploy_image
_deploy_image: base 
	@docker build -t ${ORG}/${BUILD_IMAGE} . -f Dockerfile-build

.PHONY: test
test: _test_image
	@docker run --rm -it -e PYTHONDONTWRITEBYTECODE=1 -e STREAM_PASSWORD=${STREAM_PASSWORD} -v`pwd`:/opt/src ${ORG}/${TEST_IMAGE}

.PHONY: dev
dev: _dev_image
	@docker run --rm -it --net=host ${ORG}/${DEV_IMAGE}

.PHONY: run
run:
	@docker run --rm -it --net=host ${ORG}/${IMAGE} bash

tc:
	@python test_capture.py

# deploy to PyPI, tag the version, and push to dockerhub
.PHONY: publish
publish: _deploy_image
	@docker run --rm -e PYPI_PASSWORD=${PYPI_PASSWORD} -e PYPI_USER=${PYPI_USER} ${ORG}/${BUILD_IMAGE}
	@docker tag ${ORG}/${IMAGE} ${ORG}/${IMAGE}:${VERSION}
	@docker login -u=${DOCKER_USERNAME} -p=${DOCKER_PASSWORD}
	@docker push ${ORG}/${IMAGE}:${VERSION}
