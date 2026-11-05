from django.utils.translation import gettext_lazy as _
from django import forms


class ReportPeriodForm(forms.Form):
    """Hisobot davri: kunlik / haftalik / oylik."""
    PERIODS = [("day", _("Bugun")), ("week", _("7 kun")), ("month", _("30 kun"))]
    period = forms.ChoiceField(choices=PERIODS, required=False)

    DAYS = {"day": 1, "week": 7, "month": 30}

    def days(self):
        return self.DAYS.get(self.cleaned_data.get("period") if self.is_valid() else "month", 30)
