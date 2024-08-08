# syntax=docker/dockerfile:1

ARG TOFU_IMAGE_TAG=v1.8.1
ARG TFSEC_IMAGE_TAG=v1.28.10

FROM aquasec/tfsec-alpine:${TFSEC_IMAGE_TAG} AS tfsec

FROM europe-west1-docker.pkg.dev/jobtome-platform/public/tofu:${TOFU_IMAGE_TAG}

COPY --from=tfsec /usr/bin/tfsec /usr/bin/tfsec
