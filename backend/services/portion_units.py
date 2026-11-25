"""Recognize food weights in user text and convert them to grams."""
from decimal import Decimal
import re


_GRAM_FACTORS = {
    '毫克': Decimal('0.001'), 'mg': Decimal('0.001'),
    '克': Decimal('1'), 'g': Decimal('1'),
    '千克': Decimal('1000'), '公斤': Decimal('1000'), 'kg': Decimal('1000'),
    '斤': Decimal('500'), '两': Decimal('50'),
    '磅': Decimal('453.59237'), 'lb': Decimal('453.59237'), 'lbs': Decimal('453.59237'),
    '盎司': Decimal('28.349523125'), 'oz': Decimal('28.349523125'),
}
IMPERIAL_UNITS = {'磅', 'lb', 'lbs', '盎司', 'oz'}
_SPOKEN_NUMBERS = {word: Decimal(i) for i, word in enumerate('零一二三四五六七八九十')}
_SPOKEN_NUMBERS.update({'两': Decimal(2), '半': Decimal('0.5')})

PORTION_WEIGHT = re.compile(
    r'(?<![\d.\-−])(?P<amount>\d+(?:\.\d+)?|\.\d+|'
    r'(?<![零一二两三四五六七八九十百千万点])[半一二两三四五六七八九十])\s*'
    r'(?P<unit>千克|公斤|毫克|克(?!拉)|斤|两(?!次|个|份|天)|磅|盎司|(?:kg|mg|g|lbs?|oz)(?![a-z]))',
    re.IGNORECASE,
)


def weight_in_grams(match):
    amount = match['amount']
    number = _SPOKEN_NUMBERS[amount] if amount in _SPOKEN_NUMBERS else Decimal(amount)
    return number * _GRAM_FACTORS[match['unit'].lower()]
