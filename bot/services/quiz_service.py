import random

from bot.data.epochs import EPOCHS, EPOCH_ORDER
from bot.services import europeana


async def build_bonus_question() -> dict | None:
    """Бонус: угадай эпоху по настоящему артефакту из Europeana.
    Артефакт ищется по запросу конкретной эпохи — правильный ответ известен заранее."""
    epoch_code = random.choice(EPOCH_ORDER)
    epoch = EPOCHS[epoch_code]
    items = await europeana.get_artifacts(epoch["artifact_query"], rows=3)
    if not items:
        return None  # graceful degradation: бонус просто пропускается
    item = random.choice(items)
    others = [EPOCHS[c]["plain_name"] for c in EPOCH_ORDER if c != epoch_code]
    random.shuffle(others)
    options = [epoch["plain_name"]] + others[:2]
    random.shuffle(options)
    return {"artifact": item,
            "q": "Бонус: в какую эпоху создан этот артефакт?",
            "options": options,
            "correct": options.index(epoch["plain_name"]),
            "explain": f"Артефакт из коллекции Europeana относится к эпохе «{epoch['plain_name']}»."}