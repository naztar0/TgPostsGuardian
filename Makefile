SHELL=/usr/bin/bash

all: start

app:
	@systemctl restart gunicorn
	@systemctl restart gunicorn.socket

debug:
	@python manage.py runserver 0.0.0.0:8080

start: app

install:
	@pip install -r requirements.txt

.PHONY: all app start update install
