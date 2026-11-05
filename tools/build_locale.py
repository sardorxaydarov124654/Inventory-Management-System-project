"""translations.py dan locale/*/django.po yaratadi va .mo ga kompilyatsiya qiladi.
Ishlatish:  python tools/build_locale.py   (msgid lar loyiha kodidan avtomatik yig'iladi)"""
import ast, glob, json, os, re, sys
import polib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "tools")
from translations import T  # noqa: E402

ids = {}
for f in sorted(glob.glob("templates/**/*.html", recursive=True)):
    s = open(f, encoding="utf-8").read()
    for m in re.finditer(r'\{%\s*trans\s+(?:"([^"]*)"|\'([^\']*)\')', s): ids.setdefault(m.group(1) or m.group(2), f)
    for m in re.finditer(r'\b_\(\s*"([^"]*)"\s*\)', s): ids.setdefault(m.group(1), f)
    for m in re.finditer(r'\{%\s*blocktrans[^%]*%\}(.*?)\{%\s*endblocktrans\s*%\}', s, re.S):
        ids.setdefault(re.sub(r'\{\{\s*(\w+)\s*\}\}', r'%(\1)s', m.group(1)), f)
for f in sorted(glob.glob("*/**/*.py", recursive=True)):
    if "/migrations/" in f or "management" in f or f.startswith(("config", "tools")): continue
    for n in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("_", "gettext", "gettext_lazy") \
                and n.args and isinstance(n.args[0], ast.Constant):
            ids.setdefault(n.args[0].value, f)

missing = [k for k in ids if k not in T]
if missing:
    print("Tarjimasi yo'q matnlar (tools/translations.py ga qo'shing):")
    for k in missing: print("  ", repr(k))
for idx, lang in enumerate(("ru", "en")):
    po = polib.POFile()
    po.metadata = {"Project-Id-Version": "InvenTrack", "Language": lang, "MIME-Version": "1.0",
                   "Content-Type": "text/plain; charset=UTF-8", "Content-Transfer-Encoding": "8bit",
                   "Plural-Forms": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"
                   if lang == "ru" else "nplurals=2; plural=(n != 1);"}
    for k, where in ids.items():
        if k in T: po.append(polib.POEntry(msgid=k, msgstr=T[k][idx], occurrences=[(where, "")]))
    d = f"locale/{lang}/LC_MESSAGES"; os.makedirs(d, exist_ok=True)
    po.save(d + "/django.po"); po.save_as_mofile(d + "/django.mo")
    print(lang, len(po), "ta matn kompilyatsiya qilindi")
