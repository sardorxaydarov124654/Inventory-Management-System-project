from django.conf import settings
from django.utils import translation

from .languages import detect_browser_language, language_names, language_stats


def languages(request):
    """Til tanlash oynasi uchun ma'lumotlar (barcha sahifalarda)."""
    current = (translation.get_language() or settings.LANGUAGE_CODE).split("-")[0]
    browser = detect_browser_language(request)
    stats = language_stats()
    cards = [
        {
            "code": code,
            "name": language_names(code)[0],
            "native": label,
            "current": code == current,
            "recommended": False,
        }
        for code, label in settings.LANGUAGES
    ]
    # Tavsiya: avval brauzer tili; u qo'llab-quvvatlanmasa — eng ko'p tanlangan til; u ham bo'lmasa — standart til
    has_data = any(s["count"] for s in stats)
    if browser:
        recommended, raw = browser
    else:
        recommended, raw = (stats[0]["code"] if has_data else settings.LANGUAGE_CODE), ""
    for card in cards:
        card["recommended"] = card["code"] == recommended
    suggestion = None
    if recommended != current:
        suggestion = {"code": recommended, "raw": raw, "name": language_names(recommended)[0]}
    return {
        "CUR_LANG": current,
        "CUR_LANG_NAME": language_names(current)[0],
        "LANG_CARDS": cards,
        "LANG_STATS": stats,
        "LANG_STATS_HAS_DATA": has_data,
        "LANG_TOTAL": sum(s["count"] for s in stats),
        "BROWSER_LANG": suggestion,
    }
