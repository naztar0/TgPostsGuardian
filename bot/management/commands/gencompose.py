import copy
import yaml
from django.core.management.base import BaseCommand
from app.settings import BASE_DIR, USERBOT_PN_LIST, USERBOT_HOST_LIST, HOST_FUNC_COUNT


COMPOSES = [
    {'base': BASE_DIR / 'docker-compose.base.yml', 'gen': BASE_DIR / 'docker-compose.gen.yml'},
    {'base': BASE_DIR / 'docker-compose.base.dev.yml', 'gen': BASE_DIR / 'docker-compose.gen.dev.yml'},
]


def get_service_name(phone: str, host: bool, func: int) -> str:
    sanitized = ''.join(ch for ch in phone if ch.isdigit())
    prefix = 'host' if host else 'bot'
    return f'{prefix}{func}_{sanitized}'


def gen_compose(compose: dict):
    with open(compose['base'], 'r') as f:
        base = yaml.safe_load(f)

    bot_base = base.get('x-bot-base')
    services = base.get('services')
    networks = base.get('networks')

    for phone in USERBOT_PN_LIST:
        service_name = get_service_name(phone, False, 1)
        services[service_name] = copy.deepcopy(bot_base) | {
            'environment': {
                'PHONE_NUMBER': phone,
                'HOST': '0',
                'FUNC': '0',
            }
        }

    for phone in USERBOT_HOST_LIST:
        for func in range(HOST_FUNC_COUNT):
            service_name = get_service_name(phone, True, func + 1)
            services[service_name] = copy.deepcopy(bot_base) | {
                'environment': {
                    'PHONE_NUMBER': phone,
                    'HOST': '1',
                    'FUNC': str(func + 1)
                }
            }

    generated = {
        'services': services,
        'networks': networks,
    }

    with open(compose['gen'], 'w') as f:
        yaml.dump(generated, f, sort_keys=False)

    print(f'Generated {compose['gen']} with {len(services)} services')


class Command(BaseCommand):
    def handle(self, *args, **options):
        for compose in COMPOSES:
            gen_compose(compose)
