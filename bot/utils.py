from pathlib import Path
from pyrogram import types

base_dir = Path(__file__).parent
temp_dir = base_dir / 'temp'


def get_media_file_id(message: types.Message):
    available_media = ("audio", "document", "photo", "sticker", "animation", "video", "voice", "video_note",)
    if isinstance(message, types.Message):
        for kind in available_media:
            media = getattr(message, kind, None)

            if media is not None:
                break
        else:
            return None
    else:
        media = message
    return media.file_id
