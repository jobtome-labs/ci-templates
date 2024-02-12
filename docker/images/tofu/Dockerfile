# syntax=docker/dockerfile:1

FROM alpine:3.19 AS base

ARG TOFU_VERSION=1.6.1

RUN apk add --no-cache \
    bash \
    openssl \
    curl \
    git \
    cosign

RUN curl -LO https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_amd64.apk \
    && \
    curl -LO https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_SHA256SUMS \
    && \
    curl -LO https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_SHA256SUMS.sig \
    && \
    curl -LO https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_SHA256SUMS.pem

RUN mv tofu_${TOFU_VERSION}_amd64.apk tofu_amd64.apk

RUN cosign verify-blob \
    --signature tofu_${TOFU_VERSION}_SHA256SUMS.sig \
    --certificate tofu_${TOFU_VERSION}_SHA256SUMS.pem \
    --certificate-identity https://github.com/opentofu/opentofu/.github/workflows/release.yml@refs/heads/v1.6 \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    tofu_${TOFU_VERSION}_SHA256SUMS


FROM alpine:3.19

COPY --from=base tofu_amd64.apk .

RUN apk add --allow-untrusted tofu_amd64.apk

RUN rm -f tofu_amd64.apk

RUN tofu --version
