@echo off

echo Collecting static files
python manage.py collectstatic --noinput

echo Creating translations
python manage.py makemessages -l en -l ru

echo Compiling translations
python manage.py compilemessages

echo Done
