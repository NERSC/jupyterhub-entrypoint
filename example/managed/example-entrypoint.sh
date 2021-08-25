#!/bin/bash

echo "$(date) LAUNCH"
export SOME_ENVIRONMENT_VARIABLE=123
exec "$@"
