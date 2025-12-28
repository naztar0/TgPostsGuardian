import copy
import yaml
from django.core.management.base import BaseCommand
from app.settings import BASE_DIR
from bot import models


COMPOSES = [
    {'base': BASE_DIR / 'docker-compose.base.yml', 'gen': BASE_DIR / 'docker-compose.gen.yml'},
    {'base': BASE_DIR / 'docker-compose.base.dev.yml', 'gen': BASE_DIR / 'docker-compose.gen.dev.yml'},
]


def get_service_name(phone: str, _id: int) -> str:
    return f'{_id}_{phone}'


def gen_compose(compose: dict):
    with open(compose['base'], 'r') as f:
        base = yaml.safe_load(f)

    bot_base = base.get('x-bot-base')
    services = base.get('services')
    networks = base.get('networks')

    numbers = [x.phone_number for x in models.UserBotConfig.objects.filter(is_active=True)]

    sessions = models.UserBotSession.objects \
        .filter(userbot__phone_number__in=numbers) \
        .order_by('id') \
        .select_related('userbot')

    for session in sessions:
        service_name = get_service_name(session.userbot.phone_number, session.id)
        services[service_name] = copy.deepcopy(bot_base) | {
            'environment': {
                'SESSION_ID': session.id,
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
