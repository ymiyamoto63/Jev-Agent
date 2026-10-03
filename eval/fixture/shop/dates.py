import calendar
from datetime import date


def add_months(d, months):
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, d.day)


def is_weekend(d):
    return d.weekday() >= 5


def month_end(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
