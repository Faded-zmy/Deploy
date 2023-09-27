#!/bin/bash

exec uvicorn api_server:app --host 0.0.0.0 --port 6699 --reload --workers 10

