from django.core.management.base import BaseCommand
from app.settings import BASE_DIR
import os


class Command(BaseCommand):
    def handle(self, *args, **options):
        for file in os.listdir(f'{BASE_DIR}/pids'):
            with open(f'{BASE_DIR}/pids/{file}', 'r') as f:
                pid = f.read()
            if os.name == 'posix':
                os.system(f'kill -9 {pid}')
            elif os.name == 'nt':
                os.system(f'taskkill /F /PID {pid}')
            os.remove(f'{BASE_DIR}/pids/{file}')
