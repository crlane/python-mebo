ORG?=crlane
IMAGE?=python-mebo
TEST_IMAGE?=${IMAGE}-test
BUILD_IMAGE?=${IMAGE}-build

.PHONY: image publish build _test_image test run publish

image:
	@docker build -t ${ORG}/${IMAGE} .

build: image
	@docker build -t ${ORG}/${BUILD_IMAGE} . -f Dockerfile-build

_test_image:
	@docker build -t ${ORG}/${TEST_IMAGE} . -f Dockerfile-test

test: _test_image
	@docker run --rm -it -v`pwd`/test:/opt/src/test ${ORG}/${TEST_IMAGE} py.test .

run:
	@docker run --rm -it ${ORG}/${IMAGE} bash

publish: build
	# @docker run --rm -it ${ORG}/${BUILD_IMAGE}
