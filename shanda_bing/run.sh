#!/bin/bash

exec uvicorn api_server:app --host 0.0.0.0 --port 8888 --reload --workers 10

