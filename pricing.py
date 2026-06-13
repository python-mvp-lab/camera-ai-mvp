from __future__ import annotations

import pandas as pd


def yen(amount: int | None) -> str:
    if amount is None:
        return "要相談"
    return f"¥{amount:,}"


def calculate_total(
    plan: pd.Series, selected_options: list[dict]
) -> tuple[int | None, list[dict]]:
    if str(plan["price_mode"]) != "固定":
        return None, [{"項目": "料金", "金額": "要相談", "補足": plan["notes"]}]

    total = int(plan["base_price"])
    details = [{"項目": f"基本料金：{plan['plan_variant']}", "金額": total, "補足": ""}]

    for option in selected_options:
        price = int(option["price_delta"])
        total += price
        details.append({"項目": option["option_name"], "金額": price, "補足": option.get("note", "")})

    return total, details
