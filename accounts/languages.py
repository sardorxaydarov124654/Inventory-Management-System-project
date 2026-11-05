"""Til tanlash oynasi uchun yordamchilar: nomlar, brauzer tilini aniqlash, tanlov statistikasi."""
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count

# kod -> (inglizcha nom, o'z tilidagi nom)
NAMES = {
    "uz": ("Uzbek", "O‘zbekcha"),
    "ru": ("Russian", "Русский"),
    "en": ("English", "English"),
}
STATS_KEY = "language_stats_v2"
VISITOR_COOKIE = "inventrack_visitor"


def language_names(code):
    label = dict(settings.LANGUAGES).get(code, code)
    return NAMES.get(code, (label, label))


def detect_browser_language(request):
    """Accept-Language dan saytimiz qo'llab-quvvatlaydigan birinchi tilni topadi -> (kod, xom_teg) yoki None."""
    supported = {code for code, _label in settings.LANGUAGES}
    items = []
    for order, part in enumerate(request.META.get("HTTP_ACCEPT_LANGUAGE", "").split(",")):
        tag, _sep, q = part.strip().partition(";q=")
        try:
            weight = float(q) if q else 1.0
        except ValueError:
            weight = 0.0
        if tag and weight > 0:
            items.append((-weight, order, tag))
    for _w, _o, tag in sorted(items):
        code = tag.split("-")[0].lower()
        if code in supported:
            return code, tag
    return None


def language_stats():
    """Foydalanuvchilar va mehmonlar tanlagan tillar bo'yicha foizlar (jami 100%, eng ko'pi birinchi)."""
    data = cache.get(STATS_KEY)
    if data is not None:
        return data
    from .models import LanguageChoice

    codes = [code for code, _label in settings.LANGUAGES]
    rows = LanguageChoice.objects.values("language").annotate(n=Count("id"))
    counts = {code: 0 for code in codes}
    for r in rows:
        if r["language"] in counts:
            counts[r["language"]] = r["n"]
    total = sum(counts.values())
    percent = {code: 0 for code in codes}
    if total:
        raw = {code: counts[code] * 100 / total for code in codes}
        percent = {code: int(raw[code]) for code in codes}
        left = 100 - sum(percent.values())  # eng katta qoldiq usuli: yig'indi aniq 100 bo'lsin
        for code in sorted(codes, key=lambda c: raw[c] - percent[c], reverse=True)[:left]:
            percent[code] += 1
    data = [
        {"code": c, "name": language_names(c)[0], "native": language_names(c)[1], "count": counts[c], "percent": percent[c]}
        for c in sorted(codes, key=lambda c: (-counts[c], codes.index(c)))
    ]
    cache.set(STATS_KEY, data, 60)
    return data
