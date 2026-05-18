"""Tests for lot code generation logic."""
from datetime import datetime
from app.lot_code import generate_lot_code, next_batch_number, _short_name, _short_category


def test_short_name_single_word():
    assert _short_name("Kombucha") == "KOMB"

def test_short_name_multi_word():
    assert _short_name("House Sauerkraut") == "HS"

def test_short_name_three_words():
    assert _short_name("Red Wine Vinegar") == "RWV"

def test_short_category_lab():
    assert _short_category("LAB") == "LAB"

def test_short_category_kombucha():
    assert _short_category("Kombucha") == "KOM"

def test_short_category_yeast():
    assert _short_category("Yeast") == "YST"

def test_generate_lot_code_format():
    dt = datetime(2025, 5, 16)
    code = generate_lot_code("House Sauerkraut", "LAB", dt, stage=1, batch_number=1)
    assert code == "HS-LAB-250516-S1-B1"

def test_generate_lot_code_stage2():
    dt = datetime(2025, 6, 1)
    code = generate_lot_code("Kombucha", "Kombucha", dt, stage=2, batch_number=3)
    assert code == "KOMB-KOM-250601-S2-B3"

def test_next_batch_number_empty():
    assert next_batch_number([]) == 1

def test_next_batch_number_existing():
    class FakeBatch:
        def __init__(self, n): self.batch_number = n
    batches = [FakeBatch(1), FakeBatch(2), FakeBatch(3)]
    assert next_batch_number(batches) == 4