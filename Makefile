# Use bash for shell commands
SHELL=/usr/bin/bash

# Default target: update dependencies and start the server
all: update start

# Alias to restart the application server
start: restart

# Update the project: install dependencies and compile translations
update: install compile-translations

# Restart the application server
restart:
	@systemctl restart gunicorn-pg
	@systemctl restart gunicorn-pg.socket

dev-server:
	@python manage.py runserver localhost:8000

install:
	@pip install -r requirements.txt

create-translations:
	@python manage.py makemessages -l en -l ru

compile-translations:
	@python manage.py compilemessages

collect-static:
	@python manage.py collectstatic --noinput

migrate:
	@python manage.py migrate

createsuperuser:
	@python manage.py createsuperuser

test:
	@python manage.py test

# Clean up Python cache files
clean:
	@find . -name "*.pyc" -exec rm -f {} \;
	@find . -name "*.pyo" -exec rm -f {} \;
	@find . -name "__pycache__" -exec rm -rf {} \;

# Show help message
help:
	@echo -e "\033[1mUsage:\033[0m"
	@echo "  make [target]"
	@echo ""
	@echo -e "\033[1mTargets:\033[0m"
	@echo "  all                Update dependencies and start the server"
	@echo "  restart            Restart the application server"
	@echo "  dev-server         Start the Django development server"
	@echo "  start              Alias for 'restart'"
	@echo "  update             Update dependencies and compile translations"
	@echo "  install            Install Python dependencies"
	@echo "  create-translations  Create translation files"
	@echo "  compile-translations Compile translation files"
	@echo "  collect-static     Collect static files"
	@echo "  migrate            Apply database migrations"
	@echo "  createsuperuser    Create a superuser"
	@echo "  test               Run tests"
	@echo "  clean              Clean up Python cache files"
	@echo "  help               Show this help message"
	@echo ""
	@echo -e "\033[33mActivate the virtual environment before running any target:\033[0m"
	@echo -e "  \033[4msource venv/bin/activate\033[0m"


# Declare phony targets
.PHONY: all restart dev-server start update install compile-translations collect-static migrate createsuperuser test clean help
