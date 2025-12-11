#!/bin/sh
uv run manage.py gencompose
uv run manage.py makemessages -l en -l ru
uv run manage.py compilemessages
uv run manage.py collectstatic --noinput
