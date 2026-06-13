import pandas as pd
import pytest

from pricing import calculate_total, yen


# ---------------------------------------------------------------
# yen()
# ---------------------------------------------------------------

def test_yen_formats_positive_integer():
    assert yen(25000) == "¥25,000"


def test_yen_formats_zero():
    assert yen(0) == "¥0"


def test_yen_returns_consultation_for_none():
    assert yen(None) == "要相談"


def test_yen_formats_large_amount():
    assert yen(110000) == "¥110,000"


# ---------------------------------------------------------------
# calculate_total()
# ---------------------------------------------------------------

def _make_plan(price_mode="固定", base_price=25000, plan_variant="1ヶ所プラン", notes=""):
    return pd.Series({
        "price_mode": price_mode,
        "base_price": base_price,
        "plan_variant": plan_variant,
        "notes": notes,
    })


def test_fixed_price_no_options():
    plan = _make_plan(base_price=25000)
    total, details = calculate_total(plan, [])
    assert total == 25000
    assert len(details) == 1
    assert details[0]["金額"] == 25000


def test_fixed_price_single_option():
    plan = _make_plan(base_price=25000)
    options = [{"option_name": "USBメモリ", "price_delta": 3000, "note": "USBメモリでの納品"}]
    total, details = calculate_total(plan, options)
    assert total == 28000
    assert len(details) == 2
    assert details[1]["項目"] == "USBメモリ"
    assert details[1]["金額"] == 3000


def test_fixed_price_multiple_options():
    plan = _make_plan(base_price=25000)
    options = [
        {"option_name": "1時間追加", "price_delta": 5000, "note": ""},
        {"option_name": "高山市外送料", "price_delta": 1500, "note": ""},
    ]
    total, details = calculate_total(plan, options)
    assert total == 31500
    assert len(details) == 3


def test_consultation_price_mode():
    plan = _make_plan(price_mode="要相談", base_price=0, notes="品数で変動します。要相談。")
    total, details = calculate_total(plan, [])
    assert total is None
    assert details[0]["金額"] == "要相談"


def test_consultation_ignores_options():
    """要相談プランにオプションを渡しても合計はNoneのまま"""
    plan = _make_plan(price_mode="要相談", base_price=0)
    options = [{"option_name": "USBメモリ", "price_delta": 3000, "note": ""}]
    total, details = calculate_total(plan, options)
    assert total is None


def test_option_without_note_key():
    """note キーが存在しない辞書でもエラーにならない"""
    plan = _make_plan(base_price=25000)
    options = [{"option_name": "台紙 2面", "price_delta": 12000}]
    total, details = calculate_total(plan, options)
    assert total == 37000
    assert details[1]["補足"] == ""
