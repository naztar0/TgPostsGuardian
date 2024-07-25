import os
import sys

project_home = '/root/TgPostsGuardian'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

application = get_wsgi_application()
