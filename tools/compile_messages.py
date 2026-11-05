"""msgfmt / gettext o'rnatilmagan bo'lsa ham .po -> .mo yaratadi:  python tools/compile_messages.py"""
import glob
import polib

for po_path in glob.glob("locale/*/LC_MESSAGES/django.po"):
    polib.pofile(po_path).save_as_mofile(po_path[:-3] + ".mo")
    print("compiled", po_path)
