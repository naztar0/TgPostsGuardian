@echo off

echo Collecting static files
python manage.py collectstatic --noinput

echo Creating symlinks
mklink /D %CD%\bot\app %CD%\app
mklink /D %CD%\bot\templates %CD%\templates

echo Creating translations
cd bot ^
    && django-admin makemessages -l en --symlinks ^
    && django-admin makemessages -l ru --symlinks ^
    && django-admin compilemessages ^
    && cd ..

echo Done
