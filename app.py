import os
import urllib.parse
from pathlib import Path

import pandas as pd
import streamlit as st

# =========================
# 基本設定
# =========================

st.set_page_config(
    page_title="飛騨高山 撮影プラン提案アプリ",
    page_icon="📷",
    layout="centered",
)

MASTER_DIR = Path("master")
MASTER_DIR.mkdir(exist_ok=True)

PLAN_CSV_PATH = MASTER_DIR / "plan_master.csv"
OPTION_CSV_PATH = MASTER_DIR / "option_master.csv"


NOTICE_TEXT = """
**【ご予約前にご確認ください】**

・衣装・ヘアセットのご提供はありません。ご自身でご準備をお願いいたします。【ご紹介できます】

・天候不良時の延期は1週間前までにお願いいたします。

・延期・キャンセル料はいただいておりません。体調不良等やむを得ない場合はお知らせください。

・片道30km以上の場合、別途交通費をいただきます。

・表示価格の変更がある場合がございます。ご了承ください。

・スタジオには駐車場がございません。近隣のパーキングをご利用ください。

・アルバム等をご注文いただいた場合、高山市外の方へのお届けは別途送料1,500円を頂戴いたします。

☆お客様に最高のお写真・動画をお届けするのが使命です。可能な限りご希望に添います。何でもご相談ください！
"""


# =========================
# データ読み込み
# =========================

def load_csv(path: Path, required_columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        st.error(f"{path} が見つかりません。先にCSVを作成してください。")
        st.stop()

    df = pd.read_csv(path)
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"{path.name} に不足している列があります: {missing}")
        st.stop()
    return df


def load_plan_master() -> pd.DataFrame:
    required = [
        "active", "menu_name", "plan_variant", "base_price", "price_mode",
        "shooting_time", "location_type", "delivery_count", "delivery_method",
        "recommendation", "location_comment", "notes", "display_order",
    ]
    df = load_csv(PLAN_CSV_PATH, required)

    for col in ["menu_name", "plan_variant", "price_mode"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    numeric_cols = ["active", "base_price", "display_order"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df = df[df["active"] == 1].copy()
    df = df.sort_values(["display_order", "menu_name", "plan_variant"])
    if df.empty:
        st.error("有効な撮影プランがありません。plan_master.csv の active を 1 にしてください。")
        st.stop()
    return df


def load_option_master() -> pd.DataFrame:
    required = [
        "active", "target_menu", "target_plan", "option_name", "price_delta", "selection_type",
        "group_name", "note", "display_order",
    ]
    df = load_csv(OPTION_CSV_PATH, required)

    for col in ["target_menu", "target_plan", "option_name", "selection_type", "group_name"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    numeric_cols = ["active", "price_delta", "display_order"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df = df[df["active"] == 1].copy()
    return df.sort_values(["display_order", "target_menu", "option_name"])


# =========================
# 共通関数
# =========================

def yen(amount: int | None) -> str:
    if amount is None:
        return "要相談"
    return f"¥{amount:,}"


def build_plan_result(plan: pd.Series) -> dict:
    return {
        "おすすめメニュー": plan["menu_name"],
        "プラン": plan["plan_variant"],
        "撮影時間の目安": plan["shooting_time"],
        "撮影場所": plan["location_type"],
        "納品方法": plan["delivery_method"],
        "納品枚数の目安": plan["delivery_count"],
        "提案コメント": str(plan["recommendation"]),
        "ロケーションコメント": plan["location_comment"],
        "注意事項": plan["notes"],
    }


def calculate_total(plan: pd.Series, selected_options: list[dict]) -> tuple[int | None, list[dict]]:
    if str(plan["price_mode"]) != "固定":
        return None, [{"項目": "料金", "金額": "要相談", "補足": plan["notes"]}]

    total = int(plan["base_price"])
    details = [{"項目": f"基本料金：{plan['plan_variant']}", "金額": total, "補足": ""}]

    for option in selected_options:
        price = int(option["price_delta"])
        total += price
        details.append({"項目": option["option_name"], "金額": price, "補足": option.get("note", "")})

    return total, details


def build_line_inquiry_url(line_oa_id: str, message: str) -> str:
    """
    公式LINEのトーク画面を開き、問い合わせ文を入力欄に入れるURLを作る。
    LINE_OA_ID は環境変数から読み込む。
    """

    if not line_oa_id:
        return ""

    encoded_oa_id = urllib.parse.quote(line_oa_id.strip(), safe="@")
    encoded_message = urllib.parse.quote(message)

    return f"https://line.me/R/oaMessage/{encoded_oa_id}/?{encoded_message}"


# =========================
# セッション状態
# =========================

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None
if "latest_price" not in st.session_state:
    st.session_state.latest_price = None
if "latest_price_details" not in st.session_state:
    st.session_state.latest_price_details = []
if "latest_inputs" not in st.session_state:
    st.session_state.latest_inputs = {}


# =========================
# アプリ本体
# =========================

plan_df = load_plan_master()
option_df = load_option_master()

st.title("📷 飛騨高山 撮影プラン提案アプリ")
st.info(
    "MVP v3.2：料金・プランをCSVで管理し、問い合わせは公式LINEへ誘導する版です。"
    "料金修正は master フォルダ内のCSVを編集して反映します。"
)

tab1, tab2, tab3 = st.tabs([
    "プラン提案・料金計算",
    "LINEで問い合わせる",
    "料金表確認"
])

with tab1:
    st.header("プラン提案・料金計算")

    menu_names = plan_df["menu_name"].drop_duplicates().tolist()
    selected_menu = st.selectbox("撮影メニュー", menu_names)

    filtered_plans = plan_df[plan_df["menu_name"] == selected_menu].copy()
    plan_variants = filtered_plans["plan_variant"].tolist()
    selected_variant = st.selectbox("プラン", plan_variants)

    selected_plan = filtered_plans[filtered_plans["plan_variant"] == selected_variant].iloc[0]

    st.subheader("基本情報")
    st.write(f"**基本料金：** {yen(int(selected_plan['base_price'])) if selected_plan['price_mode'] == '固定' else '要相談'}")
    st.write(f"**撮影時間：** {selected_plan['shooting_time']}")
    st.write(f"**撮影場所：** {selected_plan['location_type']}")
    st.write(f"**納品方法：** {selected_plan['delivery_method']}")
    st.write(f"**納品枚数：** {selected_plan['delivery_count']}")

    plan_mask = (option_df["target_plan"] == "") | (option_df["target_plan"] == selected_variant)
    applicable_options = option_df[(option_df["target_menu"] == selected_menu) & plan_mask].copy()

    selected_options: list[dict] = []
    if not applicable_options.empty:
        st.subheader("オプション")

        # radio形式のオプション。同じgroup_nameの中から1つだけ選ぶ。
        radio_options = applicable_options[applicable_options["selection_type"] == "radio"]
        for group_name, group_df in radio_options.groupby("group_name", sort=False):
            labels = ["なし"] + [f"{row.option_name}（+{row.price_delta:,}円）" for row in group_df.itertuples()]
            choice = st.radio(
                group_name,
                labels,
                key=f"radio_{selected_menu}_{selected_variant}_{group_name}"
            )
            if choice != "なし":
                selected_row = group_df.iloc[labels.index(choice) - 1]
                selected_options.append(selected_row.to_dict())

        # checkbox形式のオプション。複数選択できる。
        checkbox_options = applicable_options[applicable_options["selection_type"] == "checkbox"]
        for row in checkbox_options.itertuples():
            label = f"{row.option_name}（+{row.price_delta:,}円）"
            if st.checkbox(label, key=f"checkbox_{selected_menu}_{selected_variant}_{row.option_name}"):
                selected_options.append(row._asdict())

    if st.button("おすすめプランと料金を表示する"):
        result = build_plan_result(selected_plan)
        total_price, price_details = calculate_total(selected_plan, selected_options)

        st.session_state.latest_result = result
        st.session_state.latest_price = total_price
        st.session_state.latest_price_details = price_details
        st.session_state.latest_inputs = {
            "撮影メニュー": selected_menu,
            "プラン": selected_variant,
            "選択オプション": " / ".join([option["option_name"] for option in selected_options]) if selected_options else "なし",
        }

    if st.session_state.latest_result is not None:
        st.subheader("おすすめ結果")
        for key, value in st.session_state.latest_result.items():
            st.write(f"**{key}：** {value}")

        st.subheader("料金目安")
        st.write(f"**{yen(st.session_state.latest_price)}（税込目安）**")
        st.dataframe(pd.DataFrame(st.session_state.latest_price_details), use_container_width=True)
        st.caption("※ 実際の料金は撮影内容・移動距離・納品内容などにより変動します。")

with tab2:
    st.header("LINEで問い合わせる")
    st.info(NOTICE_TEXT)

    if st.session_state.latest_result is None:
        st.warning("先に『プラン提案・料金計算』タブで、おすすめプランと料金を表示してください。")
    else:
        st.write(f"**選択中の撮影メニュー：** {st.session_state.latest_inputs['撮影メニュー']}")
        st.write(f"**選択中のプラン：** {st.session_state.latest_inputs['プラン']}")
        st.write(f"**見積金額：** {yen(st.session_state.latest_price)}")

        st.divider()
        st.write("以下を入力してから「LINEで問い合わせる」ボタンを押すと、入力内容が自動でLINEのメッセージ欄に書き込まれます。")

        name = st.text_input("お名前（任意）")
        preferred_date = st.date_input("希望日")
        message = st.text_area("ご相談内容（任意）")

        line_message_lines = [
            "【撮影プランのお問い合わせ】",
            f"・撮影メニュー：{st.session_state.latest_inputs['撮影メニュー']}",
            f"・プラン：{st.session_state.latest_inputs['プラン']}",
            f"・見積金額：{yen(st.session_state.latest_price)}",
            f"・希望日：{preferred_date}",
        ]
        if name:
            line_message_lines.append(f"・お名前：{name}")
        if message:
            line_message_lines.append(f"・ご相談内容：{message}")

        line_message = "\n".join(line_message_lines)

        line_oa_id = os.environ.get("LINE_OA_ID", "")
        line_url = build_line_inquiry_url(line_oa_id, line_message)

        if line_url:
            st.link_button("LINEで問い合わせる", line_url, use_container_width=True, type="primary")
            st.caption("LINEが開いたら、内容を確認して送信してください。")
        else:
            st.warning("LINE_OA_ID が設定されていません。管理者にお問い合わせください。")
            
        with st.expander("送信内容のプレビュー"):
            st.code(line_message)

with tab3:
    st.header("料金表確認")
    st.subheader("plan_master.csv")
    st.dataframe(plan_df, use_container_width=True)
    st.subheader("option_master.csv")
    st.dataframe(option_df, use_container_width=True)
    st.caption("料金を変更したい場合は、master/plan_master.csv または master/option_master.csv を編集してください。")
