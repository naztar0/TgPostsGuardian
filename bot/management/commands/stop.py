from django.core.management.base import BaseCommand
from app.settings import BASE_DIR
import os


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('-f', '--force', action='store_true')

    def handle(self, *args, **options):
        for file in os.listdir(f'{BASE_DIR}/pids'):
            with open(f'{BASE_DIR}/pids/{file}', 'r') as f:
                pid = f.read()
            if os.name == 'posix':
                if options['force']:
                    os.system(f'kill -9 {pid}')
                else:
                    os.system(f'kill {pid}')
            elif os.name == 'nt':
                os.system(f'taskkill /F /PID {pid}')
            os.remove(f'{BASE_DIR}/pids/{file}')
