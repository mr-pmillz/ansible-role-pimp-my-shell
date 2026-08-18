#!/usr/bin/env bash

mkdir -p /root/go 2>/dev/null
[[ ":$PATH:" != *":${HOME}/go/bin:"* ]] && export PATH="${PATH}:${HOME}/go/bin"
# Set GOPATH
if [[ -z "${GOPATH}" ]]; then export GOPATH="${HOME}/go"; fi

# Add ~/.local/bin to path
[[ ":$PATH:" != *":${HOME}/.local/bin:"* ]] && export PATH="${PATH}:${HOME}/.local/bin"

# if CI exec /bin/bash
if [[ -n "$CI" ]]; then
    exec /bin/bash
else
    exec "$@"
fi
