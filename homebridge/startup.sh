#!/bin/bash

#
# Docker Homebridge Custom Startup Script - oznu/homebridge
#
# This script can be used to customise the environment and will be executed as
# the root user each time the container starts.
#
# If using this to install plugins DO NOT use `npm`. Use `pnpm`.
#
# Example installing homebridge plugin:
#
# pnpm install homebridge-dummy
#
# Example installing packages:
#
# apt-get update
# apt-get install -y python3
#
