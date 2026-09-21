
import io
import secrets
import uuid

import pandas as pd
import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="NEXUS Negotiation Game",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
ADMIN_PIN = str(st.secrets.get("ADMIN_PIN", ""))

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# =========================
# VISUAL THEME
# =========================
st.markdown(
    """
    <style>
    :root {
        --primary: #5359E8;
        --secondary: #7C3AED;
        --cyan: #06B6D4;
        --dark: #1E2248;
        --muted: #667085;
        --resource: #059669;
        --skill: #7C3AED;
        --item: #D97706;
    }
    .stApp {
        background:
            radial-gradient(circle at 7% 2%, rgba(83,89,232,.09), transparent 28%),
            radial-gradient(circle at 94% 4%, rgba(6,182,212,.08), transparent 25%),
            #F7F8FC;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg,#F0F1FF,#FAFBFF);
        border-right: 1px solid rgba(83,89,232,.12);
    }
    .hero {
        padding: 24px 28px;
        border-radius: 24px;
        background: linear-gradient(135deg,#242854 0%,#5359E8 55%,#06B6D4 120%);
        color: white;
        box-shadow: 0 16px 42px rgba(37,42,100,.20);
        margin-bottom: 18px;
    }
    .hero h1 {margin:0;font-size:2.35rem;letter-spacing:-.04em}
    .hero p {margin:7px 0 0;opacity:.88}
    .period-card {
        padding:20px 22px;border-radius:20px;
        background:linear-gradient(135deg,#F3F2FF,#EFFBFF);
        border:1px solid #D7D9FF;box-shadow:0 9px 25px rgba(43,47,110,.08);
        margin:10px 0 18px;
    }
    .period-title {font-size:1.35rem;font-weight:850;color:#282B67}
    .period-range {font-size:.86rem;color:#667085;text-transform:uppercase;letter-spacing:.07em}
    .period-text {color:#475467;line-height:1.55;margin-top:7px}
    .team-banner {
        background:white;border:1px solid #EAECF5;border-radius:18px;
        padding:17px 20px;box-shadow:0 7px 22px rgba(30,34,72,.07);margin-bottom:10px;
    }
    .team-title {font-size:1.55rem;font-weight:850;color:#272A5D}
    .team-sub {color:#667085;margin-top:4px}
    .mission {
        padding:18px 20px;border-radius:18px;
        background:linear-gradient(135deg,#FFF8E7,#FFF0C2);
        border:1px solid #EED078;margin:8px 0 15px;
    }
    .mission strong {color:#704900}
    .mission p {color:#66551C;margin:.35rem 0}
    .asset-card {
        background:white;border:1px solid #EAECF5;border-radius:16px;
        padding:13px 15px;box-shadow:0 5px 17px rgba(30,34,72,.055);
        min-height:108px;margin-bottom:8px;
    }
    .asset-card.resource {border-top:4px solid var(--resource)}
    .asset-card.skill {border-top:4px solid var(--skill)}
    .asset-card.item {border-top:4px solid var(--item)}
    .asset-type {font-size:.7rem;color:#98A2B3;letter-spacing:.08em;text-transform:uppercase}
    .asset-name {font-weight:800;color:#25284B;margin-top:5px}
    .asset-qty {font-size:1.65rem;font-weight:900;color:#171A2B;margin-top:5px}
    .flash {
        padding:15px 18px;border-radius:16px;
        background:linear-gradient(135deg,#E9FFF6,#F4FFFB);
        border:1px solid #86DCB8;color:#116443;font-weight:800;
        animation:pop .35s ease-out;margin-bottom:12px;
    }
    .transition {
        padding:23px 24px;border-radius:22px;
        background:linear-gradient(135deg,#282D70,#5960EB,#08AFC9);
        color:white;box-shadow:0 16px 40px rgba(45,50,120,.22);margin:8px 0 18px;
        animation:pop .45s ease-out;
    }
    .transition .big {font-size:1.75rem;font-weight:900}
    .transition .small {opacity:.9;margin-top:5px}
    @keyframes pop {0%{opacity:0;transform:scale(.96)}100%{opacity:1;transform:scale(1)}}
    div[data-testid="stMetric"] {
        background:white;border:1px solid #EAECF5;padding:12px 14px;
        border-radius:15px;box-shadow:0 5px 16px rgba(30,34,72,.05);
    }
    .stButton>button {border-radius:12px;font-weight:750;min-height:42px}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# DB HELPERS
# =========================
def q(table):
    return sb.table(table)

def rpc(name, params):
    return sb.rpc(name, params).execute().data

@st.cache_data(ttl=20)
def get_games():
    return (
        q("nexus_games")
        .select("id,name,class_label,current_period,market_open,game_status,team_login_visible,public_visible")
        .order("created_at", desc=True)
        .execute().data
    )

@st.cache_data(ttl=60)
def get_assets():
    rows = (
        q("nexus_assets")
        .select("id,code,name,category,emoji")
        .eq("active", True)
        .execute().data
    )
    return rows, {r["id"]: r for r in rows}, {r["code"]: r for r in rows}

@st.cache_data(ttl=60)
def get_period_def(period):
    rows = q("nexus_period_definitions").select("*").eq("period", int(period)).execute().data
    return rows[0] if rows else None

def get_game(game_id):
    return q("nexus_games").select("*").eq("id", game_id).single().execute().data

def get_team(team_id):
    return q("nexus_teams").select("*").eq("id", team_id).single().execute().data

def get_members(team_id):
    return (
        q("nexus_members").select("full_name,display_order")
        .eq("team_id", team_id).order("display_order").execute().data
    )

def save_members(team_id, names):
    q("nexus_members").delete().eq("team_id", team_id).execute()
    clean = [x.strip() for x in names if x.strip()]
    if clean:
        q("nexus_members").insert([
            {"team_id": team_id, "full_name": name, "display_order": i + 1}
            for i, name in enumerate(clean)
        ]).execute()

def get_inventory(team_id):
    _, by_id, _ = get_assets()
    rows = (
        q("nexus_inventory").select("asset_id,quantity")
        .eq("team_id", team_id).gt("quantity", 0).execute().data
    )
    result = []
    for r in rows:
        a = by_id.get(r["asset_id"], {})
        result.append({
            "asset_id": r["asset_id"], "code": a.get("code"), "name": a.get("name", ""),
            "emoji": a.get("emoji", ""), "category": a.get("category", ""),
            "quantity": r["quantity"], "asset": f'{a.get("emoji","")} {a.get("name","")}'.strip()
        })
    order = {"resource": 0, "skill": 1, "item": 2}
    return sorted(result, key=lambda x: (order.get(x["category"], 9), x["name"]))

def get_directory(game_id):
    _, by_id, _ = get_assets()
    teams = (
        q("nexus_teams").select("id,team_no,team_name,specialization_asset_id")
        .eq("game_id", game_id).order("team_no").execute().data
    )
    out = []
    for t in teams:
        a = by_id[t["specialization_asset_id"]]
        holdings = [
            f'{x.get("emoji","")} {x["name"]}'
            for x in get_inventory(t["id"])
            if x["category"] in ("resource", "skill") and int(x["quantity"]) > 0
        ]
        out.append({
            "Team": t["team_name"],
            "Specialisation": f'{a.get("emoji","")} {a["name"]}',
            "Currently holds (type only)": ", ".join(holdings) if holdings else "—",
            "Members": ", ".join(m["full_name"] for m in get_members(t["id"]))
        })
    return out

def get_market_prices(game_id, period):
    _, by_id, _ = get_assets()
    rows = (
        q("nexus_market_prices").select("asset_id,buy_price")
        .eq("game_id", game_id).eq("period", int(period)).execute().data
    )
    out = []
    for r in rows:
        a = by_id[r["asset_id"]]
        out.append({
            "Asset": f'{a.get("emoji","")} {a["name"]}',
            "Category": a["category"],
            "Price": r["buy_price"],
            "asset_id": r["asset_id"]
        })
    return out


def get_black_market_lots(game_id, period=None):
    query = q("nexus_black_market_lots").select("*").eq("game_id", game_id)
    if period is not None:
        query = query.eq("period", int(period))
    return query.order("created_at").execute().data


def get_black_market_bids(lot_id):
    return (
        q("nexus_black_market_bids").select("*").eq("lot_id", lot_id)
        .order("bid_price_per_unit", desc=True).order("created_at").execute().data
    )


def black_market_suggestions(lot, bids):
    """Rank pending bids by unit price, then earlier bid time; allocate until supply is exhausted."""
    pending = [b for b in bids if b.get("status") == "pending"]
    pending.sort(key=lambda b: (-int(b["bid_price_per_unit"]), b.get("created_at") or ""))
    remaining = int(lot.get("quantity_remaining") or 0)
    out = []
    for rank, b in enumerate(pending, start=1):
        suggested = min(int(b["quantity_requested"]), remaining)
        remaining -= suggested
        row = dict(b)
        row["rank"] = rank
        row["suggested_quantity"] = suggested
        row["suggested_cost"] = suggested * int(b["bid_price_per_unit"])
        out.append(row)
    return out

def get_mission(team_id):
    team = get_team(team_id)
    mid = team.get("secret_mission_id")
    if not mid:
        return None
    rows = q("nexus_secret_missions").select("*").eq("id", mid).execute().data
    return rows[0] if rows else None

def team_name(team_id):
    if not team_id:
        return "International Market"
    return get_team(team_id)["team_name"]

def verify_team_login(game_id, team_no, code):
    return rpc("nexus_verify_team_login", {
        "p_game_id": game_id, "p_team_no": int(team_no), "p_code": str(code)
    })

def get_pending(team_id):
    return (
        q("nexus_transactions").select("*")
        .eq("counterparty_team_id", team_id).eq("status", "pending")
        .order("created_at", desc=True).execute().data
    )

def tx_lines(tx_id):
    return q("nexus_transaction_lines").select("*").eq("transaction_id", tx_id).execute().data

def describe_tx(tx):
    _, by_id, _ = get_assets()
    a_side, b_side = [], []
    for line in tx_lines(tx["id"]):
        if line["asset_id"]:
            a = by_id[line["asset_id"]]
            text = f'{line["quantity"]} × {a.get("emoji","")} {a["name"]}'
        else:
            text = f'{line["credits"]} Credits'
        if line["from_team_id"] == tx["proposer_team_id"]:
            a_side.append(text)
        else:
            b_side.append(text)
    return " + ".join(a_side), " + ".join(b_side)

def get_latest_completed(team_id, game_id):
    rows = (
        q("nexus_transactions").select("id,completed_at")
        .eq("game_id", game_id).eq("status", "completed")
        .or_(f"proposer_team_id.eq.{team_id},counterparty_team_id.eq.{team_id}")
        .order("completed_at", desc=True).limit(1).execute().data
    )
    return rows[0] if rows else None

def get_final_score(team_id):
    rows = q("nexus_final_scores").select("*").eq("team_id", team_id).execute().data
    return rows[0] if rows else None

# =========================
# UI HELPERS
# =========================
def set_flash(kind, message, period=None):
    st.session_state["_flash"] = {"kind": kind, "message": message, "period": period}

def render_flash():
    f = st.session_state.pop("_flash", None)
    if not f:
        return
    if f["kind"] == "period":
        p = get_period_def(f.get("period"))
        title = p["title"] if p else f'Period {f.get("period")}'
        rng = p["date_range"] if p else ""
        st.markdown(
            f'<div class="transition"><div class="big">✨ PERIOD {f.get("period")} UNLOCKED · {title}</div>'
            f'<div class="small">{rng} · {f["message"]}</div></div>',
            unsafe_allow_html=True
        )
        st.balloons()
    else:
        st.markdown(f'<div class="flash">✨ {f["message"]}</div>', unsafe_allow_html=True)
        st.toast(f["message"], icon="✅")
        if f["kind"] in ("trade", "build"):
            st.balloons()

def render_period_card(period):
    p = get_period_def(period)
    if not p:
        return
    st.markdown(
        f"""<div class="period-card">
        <div class="period-range">PERIOD {period} · {p["date_range"]}</div>
        <div class="period-title">{p.get("emoji","")} {p["title"]}</div>
        <div class="period-text"><b>Bối cảnh:</b> {p["intro"]}</div>
        <div class="period-text"><b>Cảm hứng lịch sử:</b> {p["historical_context"]}</div>
        <div class="period-text"><b>Hàm ý thị trường:</b> {p["theme_note"]}</div>
        </div>""", unsafe_allow_html=True
    )
    st.caption("Giá trong game là mô phỏng lấy cảm hứng từ các bước ngoặt lịch sử, không phải chuỗi giá lịch sử thực tế.")

def render_inventory(items):
    if not items:
        st.info("Chưa có tài sản.")
        return
    for i in range(0, len(items), 4):
        cols = st.columns(4)
        for c, x in zip(cols, items[i:i+4]):
            with c:
                st.markdown(
                    f"""<div class="asset-card {x["category"]}">
                    <div class="asset-type">{x["category"]}</div>
                    <div class="asset-name">{x["emoji"]} {x["name"]}</div>
                    <div class="asset-qty">× {x["quantity"]}</div>
                    </div>""", unsafe_allow_html=True
                )

def render_market_tables(game_id, period):
    rows = get_market_prices(game_id, period)
    labels = [("resource", "🧱 Resources"), ("skill", "🧠 Skills"), ("item", "🏆 Completed Items")]
    for category, title in labels:
        st.markdown(f"### {title}")
        data = [{"Asset": r["Asset"], "International Market": r["Price"]} for r in rows if r["Category"] == category]
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def game_selector(include_test=False):
    games = get_games()
    if not include_test:
        games = [g for g in games if g.get("team_login_visible", True)]
    opts = {f'{g["name"]} · {g["game_status"].upper()}': g["id"] for g in games}
    return opts[st.selectbox("Game session", list(opts.keys()))]

def get_public_game_id():
    """Read the currently broadcast class directly from the games table."""
    try:
        rows = (
            q("nexus_games")
            .select("id")
            .eq("public_visible", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return rows[0]["id"] if rows else None
    except Exception:
        return None

def set_public_game(game_id):
    """Teacher-only backend action: broadcast exactly one class on Public Market."""
    # Streamlit uses the server-side Supabase secret key, so these writes bypass
    # client-side RLS without exposing database credentials to students.
    q("nexus_games").update({"public_visible": False}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
    q("nexus_games").update({"public_visible": True}).eq("id", game_id).execute()
    return True

def get_device_token():
    token = st.query_params.get("td")
    if isinstance(token, list):
        token = token[0] if token else None
    if not token:
        token = uuid.uuid4().hex
        st.query_params["td"] = token
    return str(token)

def is_trader_device(team_id):
    token = get_device_token()
    try:
        return bool(rpc("nexus_verify_trader_device", {"p_team_id": team_id, "p_device_token": token}))
    except Exception:
        return False

def require_trader(team_id):
    if not is_trader_device(team_id):
        raise RuntimeError("Thiết bị này chưa được cấp quyền Trader Device.")

@st.fragment(run_every="5s")
def live_team_strip(team_id, game_id):
    team = get_team(team_id)
    game = get_game(game_id)
    pending = get_pending(team_id)
    current_period = int(game["current_period"])

    if "_seen_period" not in st.session_state:
        st.session_state["_seen_period"] = current_period
    elif current_period != st.session_state["_seen_period"]:
        st.session_state["_seen_period"] = current_period
        if current_period == 4 or game.get("game_status") == "ended":
            set_flash(
                "period",
                "FINAL REVEAL: P4 chỉ dùng để định giá danh mục cuối. Trade / Build / Sell đã kết thúc.",
                4
            )
        else:
            set_flash(
                "period",
                "Thời kỳ mới đã được mở khóa. Đọc bối cảnh, chuẩn bị BATNA rồi chờ GV mở Market.",
                current_period
            )
        st.rerun()

    latest = get_latest_completed(team_id, game_id)
    lid = latest["id"] if latest else None
    if "_last_tx" not in st.session_state:
        st.session_state["_last_tx"] = lid
    elif lid and lid != st.session_state["_last_tx"]:
        st.session_state["_last_tx"] = lid
        set_flash("trade", "Một giao dịch của team vừa được hoàn tất!")
        st.rerun()

    trader = is_trader_device(team_id)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Cash", team["cash"])
    c2.metric("🕰️ Period", current_period)
    c3.metric("📨 Offers", len(pending))
    c4.metric("Market", "OPEN" if game["market_open"] else "CLOSED")
    c5.metric("Device Access", "TRADER" if trader else "TEAM · ACCEPT ENABLED")

    if pending:
        st.markdown("### 📨 Live Inbox")
        for tx in pending:
            a, b = describe_tx(tx)
            with st.container(border=True):
                st.write(f"**{team_name(tx['proposer_team_id'])} gửi đề nghị**")
                left, mid, right = st.columns([1, .2, 1])
                left.info(f"Họ đưa\n\n**{a}**")
                mid.markdown("<h2 style='text-align:center'>⇄</h2>", unsafe_allow_html=True)
                right.warning(f"Bạn đưa\n\n**{b}**")
                ac, rj = st.columns(2)
                # Any logged-in team device may accept an incoming offer.
                # Only proactive actions such as Send Offer remain Trader-Device-only.
                accept_disabled = (not game["market_open"] or game["game_status"] != "running")
                if ac.button("🤝 Accept", key=f"a_{tx['id']}", type="primary", use_container_width=True, disabled=accept_disabled):
                    try:
                        rpc("nexus_accept_trade", {"p_transaction_id": tx["id"], "p_accepting_team_id": team_id})
                        st.session_state["_last_tx"] = tx["id"]
                        set_flash("trade", "Giao dịch thành công. Tài sản đã được chuyển.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                if rj.button("Reject", key=f"r_{tx['id']}", use_container_width=True, disabled=not trader):
                    try:
                        require_trader(team_id)
                        rpc("nexus_reject_trade", {"p_transaction_id": tx["id"], "p_rejecting_team_id": team_id})
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
    else:
        st.caption("📡 Live Inbox tự kiểm tra offer mới mỗi 5 giây.")

# =========================
# EXPORT
# =========================
def export_game_xlsx(game_id):
    game = get_game(game_id)
    _, by_id, _ = get_assets()
    teams = q("nexus_teams").select("*").eq("game_id", game_id).order("team_no").execute().data

    team_rows = []
    for t in teams:
        spec = by_id[t["specialization_asset_id"]]["name"]
        team_rows.append({
            "Team": t["team_name"], "Specialisation": spec,
            "Members": ", ".join(m["full_name"] for m in get_members(t["id"])),
            "Cash": t["cash"]
        })

    txs = q("nexus_transactions").select("*").eq("game_id", game_id).order("created_at").execute().data
    tx_rows = []
    for x in txs:
        a, b = describe_tx(x) if x["transaction_type"] == "team_trade" else ("", "")
        tx_rows.append({
            "Period": x["period"], "Type": x["transaction_type"],
            "Proposer": team_name(x["proposer_team_id"]) if x["proposer_team_id"] else "",
            "Counterparty": team_name(x["counterparty_team_id"]) if x["counterparty_team_id"] else "",
            "Proposer gives": a, "Counterparty gives": b,
            "Status": x["status"], "Reversed": x.get("reversed", False),
            "Created": x["created_at"], "Completed": x["completed_at"], "Note": x["note"]
        })

    builds = q("nexus_builds").select("*").eq("game_id", game_id).order("created_at").execute().data
    recipe_rows = q("nexus_recipes").select("*").execute().data
    recipes = {r["id"]: r for r in recipe_rows}
    build_rows = []
    for b in builds:
        r = recipes[b["recipe_id"]]
        build_rows.append({
            "Period": b["period"], "Team": team_name(b["team_id"]),
            "Output": by_id[r["output_asset_id"]]["name"], "Quantity": b["output_quantity"],
            "Resource": by_id[r["resource_asset_id"]]["name"],
            "Skill": by_id[r["skill_asset_id"]]["name"],
            "Reversed": b.get("reversed", False), "Created": b["created_at"]
        })

    inv_rows = []
    p4 = {r["asset_id"]: r["Price"] for r in get_market_prices(game_id, 4)}
    for t in teams:
        for x in get_inventory(t["id"]):
            inv_rows.append({
                "Team": t["team_name"], "Asset": x["name"], "Category": x["category"],
                "Quantity": x["quantity"], "P4 Market Price": p4.get(x["asset_id"], 0),
                "P4 Value": x["quantity"] * p4.get(x["asset_id"], 0)
            })

    score_rows = []
    scores = q("nexus_final_scores").select("*").eq("game_id", game_id).order("final_rank").execute().data
    for s in scores:
        m = get_mission(s["team_id"])
        score_rows.append({
            "Rank": s["final_rank"], "Team": team_name(s["team_id"]),
            "Mission": m["title"] if m else "",
            "Metric": s["mission_metric"], "Mission Level": s["mission_multiplier"],
            "Base Wealth": s["base_wealth"], "Mission Bonus": s["mission_bonus"],
            "Final Wealth": s["final_wealth"]
        })

    bm_rows = []
    lots = get_black_market_lots(game_id)
    for lot in lots:
        asset = by_id[lot["asset_id"]]
        for b in get_black_market_bids(lot["id"]):
            bm_rows.append({
                "Period": lot["period"], "Asset": asset["name"],
                "Lot supply": lot["quantity_total"], "Lot remaining": lot["quantity_remaining"],
                "Lot status": lot["status"], "Team": team_name(b["team_id"]),
                "Qty wanted": b["quantity_requested"], "Bid / unit": b["bid_price_per_unit"],
                "Bid status": b["status"], "Approved qty": b["approved_quantity"],
                "Created": b["created_at"]
            })

    buf = io.BytesIO()

    export_sheets = {
        "Teams": pd.DataFrame(
            team_rows,
            columns=["Team", "Specialisation", "Members", "Cash"]
        ),
        "Transactions": pd.DataFrame(
            tx_rows,
            columns=[
                "Period", "Type", "Proposer", "Counterparty",
                "Proposer gives", "Counterparty gives",
                "Status", "Reversed", "Created", "Completed", "Note"
            ]
        ),
        "Builds": pd.DataFrame(
            build_rows,
            columns=[
                "Period", "Team", "Output", "Quantity",
                "Resource", "Skill", "Reversed", "Created"
            ]
        ),
        "Black Market": pd.DataFrame(
            bm_rows,
            columns=[
                "Period", "Asset", "Lot supply", "Lot remaining", "Lot status", "Team",
                "Qty wanted", "Bid / unit", "Bid status", "Approved qty", "Created"
            ]
        ),
        "Final Inventory": pd.DataFrame(
            inv_rows,
            columns=[
                "Team", "Asset", "Category", "Quantity",
                "P4 Market Price", "P4 Value"
            ]
        ),
        "Final Ranking": pd.DataFrame(
            score_rows,
            columns=[
                "Rank", "Team", "Mission", "Metric", "Mission Level",
                "Base Wealth", "Mission Bonus", "Final Wealth"
            ]
        ),
    }

    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        for sheet_name, df in export_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            sheet = writer.sheets[sheet_name]

            # Robust even when the sheet has zero data rows.
            n_rows = max(len(df), 1)
            n_cols = max(len(df.columns), 1)

            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, n_rows, n_cols - 1)
            sheet.set_column(0, n_cols - 1, 18)

            for idx, col in enumerate(df.columns):
                if col in {
                    "Members", "Proposer gives", "Counterparty gives",
                    "Note", "Mission"
                }:
                    sheet.set_column(idx, idx, 28)

    buf.seek(0)
    return buf.getvalue()

# =========================
# HEADER
# =========================
st.markdown(
    '<div class="hero"><h1>🧩 NEXUS</h1>'
    '<p>Four Eras Negotiation Game · Trade smart · Build value · Manage your BATNA</p></div>',
    unsafe_allow_html=True
)
render_flash()
mode = st.sidebar.radio("Mode", ["🌐 Public Market & Directory", "🤝 Team", "🎛️ Teacher"])

# =========================
# PUBLIC
# =========================
if mode == "🌐 Public Market & Directory":
    game_id = get_public_game_id()
    if not game_id:
        st.warning("GV chưa chọn lớp để hiển thị trên Public Market.")
        st.stop()

    game = get_game(game_id)
    st.markdown(
        f'<div class="team-banner"><div class="team-title">📡 PUBLIC MARKET · {game["name"]}</div>'
        f'<div class="team-sub">Đây là lớp đang được GV chọn để phát công khai · '
        f'Status: {game["game_status"].upper()} · Market: '
        f'{"🟢 OPEN" if game["market_open"] else "🔴 CLOSED"}</div></div>',
        unsafe_allow_html=True
    )
    render_period_card(game["current_period"])
    t1, t2 = st.tabs(["💹 International Market", "👥 Team Directory"])
    with t1:
        render_market_tables(game_id, game["current_period"])
        st.caption("Giá Team-to-Team có thể cao hơn hoặc thấp hơn International Market tùy đàm phán.")
    with t2:
        st.dataframe(pd.DataFrame(get_directory(game_id)), use_container_width=True, hide_index=True)

# =========================
# TEAM
# =========================
elif mode == "🤝 Team":
    if "team_id" not in st.session_state:
        st.markdown("## Team Login")
        game_id = game_selector(include_test=False)
        c1, c2 = st.columns(2)
        team_no = c1.number_input("Team number", min_value=1, step=1)
        login_code = c2.text_input("Team Login Code", type="password")
        if st.button("Enter Team", type="primary", use_container_width=True):
            tid = verify_team_login(game_id, team_no, login_code)
            if tid:
                st.session_state["team_id"] = tid
                st.session_state["game_id"] = game_id
                st.session_state["_seen_period"] = get_game(game_id)["current_period"]
                latest = get_latest_completed(tid, game_id)
                st.session_state["_last_tx"] = latest["id"] if latest else None
                st.rerun()
            else:
                st.error("Sai Team number hoặc Team Login Code.")
        st.stop()

    team_id = st.session_state["team_id"]
    game_id = st.session_state["game_id"]
    team = get_team(team_id)
    game = get_game(game_id)
    assets, by_id, by_code = get_assets()
    spec = by_id[team["specialization_asset_id"]]
    members = get_members(team_id)

    st.markdown(
        f'<div class="team-banner"><div class="team-title">{team["team_name"]}</div>'
        f'<div class="team-sub">{spec.get("emoji","")} {spec["name"]} · '
        f'{", ".join(m["full_name"] for m in members) if members else "Chưa nhập thành viên"}</div></div>',
        unsafe_allow_html=True
    )
    lo, _ = st.columns([1, 5])
    if lo.button("Log out"):
        for k in ["team_id", "game_id", "_seen_period", "_last_tx"]:
            st.session_state.pop(k, None)
        st.rerun()

    trader = is_trader_device(team_id)
    if not trader:
        with st.expander("🔐 Kích hoạt Trader Device", expanded=False):
            st.caption("Chỉ một thiết bị của team được claim quyền giao dịch. Các thiết bị khác vẫn xem được thông tin team.")
            trade_code = st.text_input("Trader Device Code", type="password")
            if st.button("Claim this device as Trader", type="primary"):
                try:
                    rpc("nexus_claim_trader_device", {
                        "p_team_id": team_id,
                        "p_trade_code": trade_code,
                        "p_device_token": get_device_token()
                    })
                    set_flash("profile", "Thiết bị này đã được khóa làm Trader Device.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        st.success("🔐 Trader Device ACTIVE — thiết bị này có quyền Send Offer / Build / Sell và các thao tác chủ động. Mọi thiết bị của team vẫn có thể Accept offer đến.")

    # Claim any newly reached Secret Mission level during active gameplay.
    # The server is idempotent: refreshing/opening multiple devices cannot pay twice.
    mission_claim = None
    if game["game_status"] == "in_progress" and int(game["current_period"]) <= 3:
        try:
            mission_claim = rpc("nexus_claim_mission_progress", {"p_team_id": team_id})
        except Exception:
            mission_claim = None

    live_team_strip(team_id, game_id)
    render_period_card(game["current_period"])

    if game["game_status"] == "ended":
        score = get_final_score(team_id)
        st.markdown("## 🏁 Final Result")
        if score:
            c1, c2, c3 = st.columns(3)
            c1.metric("Base Wealth", int(score["base_wealth"]))
            c2.metric(
                "Mission Reward Earned",
                int(score["mission_bonus"]),
                f'Level {int(score["mission_multiplier"])} · already included in Cash'
                if int(score["mission_multiplier"]) > 0 else "Not completed"
            )
            c3.metric("FINAL WEALTH", int(score["final_wealth"]))
            st.info("Xếp hạng cuối không hiển thị cho sinh viên. Chỉ giảng viên xem được ranking.")
        st.divider()

    tabs = st.tabs(["🏠 My Team", "🤝 Trade", "🛠️ Build", "🌍 Market", "🕳️ Black Market", "🧾 History"])

    with tabs[0]:
        mission = get_mission(team_id)
        if mission:
            t1 = float(mission.get("threshold_value") or 0)
            t2 = float(mission.get("tier2_threshold") or 0)
            t3 = float(mission.get("tier3_threshold") or 0)

            if mission_claim:
                metric = float(mission_claim.get("metric") or 0)
                level = int(mission_claim.get("level") or 0)
                current_bonus = int(mission_claim.get("total_bonus") or 0)
                payout = int(mission_claim.get("payout") or 0)
            else:
                metric = float(rpc("nexus_mission_metric", {"p_team_id": team_id}) or 0)
                if t3 and metric >= t3:
                    level, current_bonus = 3, 200
                elif t2 and metric >= t2:
                    level, current_bonus = 2, 150
                elif t1 and metric >= t1:
                    level, current_bonus = 1, 100
                else:
                    level, current_bonus = 0, 0
                payout = 0

            if payout > 0:
                st.success(
                    f"🎯 SECRET MISSION LEVEL {level} ACHIEVED! "
                    f"+{payout} Credits have been added to your team cash. "
                    f"Total Mission Reward earned: +{current_bonus} Credits."
                )
                st.toast(f"Mission Level {level}: +{payout} Credits!", icon="🎯")
                st.balloons()

            next_target = t1 if level == 0 else (t2 if level == 1 else (t3 if level == 2 else None))
            next_text = f' · <b>Next target:</b> {next_target:g}' if next_target else ' · <b>Max level reached</b>'

            st.markdown(
                f"""<div class="mission"><strong>🔒 SECRET MISSION · {mission["title"]}</strong>
                <p>{mission["description"]}</p>
                <p><b>Progress:</b> {metric:g} · <b>Current level:</b> {level} ·
                <b>Total reward earned:</b> +{current_bonus}{next_text}</p>
                <p><b>Reward ladder:</b> Level 1 = +100 · Level 2 = +50 more (150 total) ·
                Level 3 = +100 more (250 total)</p>
                <p>Mission rewards are added to <b>Cash immediately</b> and can be used in later negotiations.</p></div>""",
                unsafe_allow_html=True
            )

        st.markdown("### 👥 Thành viên")
        cur = "\n".join(m["full_name"] for m in members)
        with st.form("members"):
            text = st.text_area("Mỗi dòng một người", value=cur, height=130)
            saved = st.form_submit_button("💾 Lưu tên thành viên", type="primary")
        if saved:
            names = [x.strip() for x in text.splitlines() if x.strip()]
            if not 3 <= len(names) <= 6:
                st.error("Nhập 3–6 thành viên.")
            else:
                save_members(team_id, names)
                st.cache_data.clear()
                set_flash("profile", "Đã cập nhật tên thành viên.")
                st.rerun()

        st.markdown("### 🎒 Inventory")
        render_inventory(get_inventory(team_id))
        if game["game_status"] == "setup":
            st.info("SETUP MODE: hãy nhập tên, đọc Secret Mission và xem thị trường. GV chưa mở giao dịch.")

    with tabs[1]:
        st.markdown("### 🤝 Create Trade Offer")
        if not trader:
            st.info("📨 Mọi thiết bị của team có thể Accept offer đến. Chỉ Trader Device mới được Send Offer.")
        if game["game_status"] != "running":
            st.info("Trade chỉ mở khi game đang RUNNING.")
        if not game["market_open"]:
            st.info("Market đang đóng.")

        directory = (
            q("nexus_teams").select("id,team_no,team_name").eq("game_id", game_id)
            .neq("id", team_id).order("team_no").execute().data
        )
        opts = {t["team_name"]: t["id"] for t in directory}
        target = st.selectbox("Counterparty", list(opts.keys()))
        left, right = st.columns(2)

        with left:
            st.markdown("#### 📤 I GIVE")
            typ = st.radio("Type", ["Asset", "Credits"], horizontal=True, key="give_type")
            if typ == "Asset":
                inv = get_inventory(team_id)
                iopts = {f'{x["asset"]} · have {x["quantity"]}': x["code"] for x in inv}
                if iopts:
                    lab = st.selectbox("Asset", list(iopts.keys()))
                    qty = st.number_input("Quantity", 1, step=1, key="gqty")
                    give = [{"asset_code": iopts[lab], "quantity": int(qty)}]
                else:
                    give = None
                    st.warning("No asset available.")
            else:
                cr = st.number_input("Credits", 1, step=1, key="gcr")
                give = [{"credits": int(cr)}]

        with right:
            st.markdown("#### 📥 I REQUEST")
            typ2 = st.radio("Type ", ["Asset", "Credits"], horizontal=True, key="req_type")
            if typ2 == "Asset":
                aopts = {f'{a.get("emoji","")} {a["name"]}': a["code"] for a in assets}
                lab2 = st.selectbox("Requested asset", list(aopts.keys()))
                qty2 = st.number_input("Requested quantity", 1, step=1, key="rqty")
                request = [{"asset_code": aopts[lab2], "quantity": int(qty2)}]
            else:
                cr2 = st.number_input("Credits requested", 1, step=1, key="rcr")
                request = [{"credits": int(cr2)}]

        disabled = (not trader or game["game_status"] != "running" or not game["market_open"] or give is None)
        if st.button("📨 Send Offer", type="primary", use_container_width=True, disabled=disabled):
            try:
                require_trader(team_id)
                rpc("nexus_create_trade", {
                    "p_game_id": game_id,
                    "p_proposer_team_id": team_id,
                    "p_counterparty_team_id": opts[target],
                    "p_period": int(game["current_period"]),
                    "p_proposer_gives": give,
                    "p_counterparty_gives": request,
                    "p_note": None
                })
                st.toast("Offer đã được gửi!", icon="📨")
            except Exception as e:
                st.error(str(e))

    with tabs[2]:
        st.markdown("### 🛠️ Build")
        recipes = q("nexus_recipes").select("*").execute().data
        ropts = {}
        for r in recipes:
            out = by_id[r["output_asset_id"]]
            res = by_id[r["resource_asset_id"]]
            sk = by_id[r["skill_asset_id"]]
            ropts[f'{out.get("emoji","")} {out["name"]} ← {res["name"]} + {sk["name"]}'] = out["code"]
        choice = st.selectbox("Recipe", list(ropts.keys()))
        bqty = st.number_input("Build quantity", 1, step=1)
        disabled = (not trader or game["game_status"] != "running" or not game["market_open"])
        if st.button("✨ BUILD", type="primary", use_container_width=True, disabled=disabled):
            try:
                require_trader(team_id)
                rpc("nexus_build_item", {
                    "p_game_id": game_id,
                    "p_team_id": team_id,
                    "p_output_asset_code": ropts[choice],
                    "p_quantity": int(bqty)
                })
                set_flash("build", f"Build thành công ×{int(bqty)}!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with tabs[3]:
        st.markdown("### 🌍 International Market")
        render_market_tables(game_id, game["current_period"])
        st.divider()
        st.markdown("### Sell")
        inv = get_inventory(team_id)
        raw = {r["asset_id"]: r["Price"] for r in get_market_prices(game_id, game["current_period"])}
        sopts = {}
        for x in inv:
            if x["asset_id"] in raw:
                sopts[f'{x["asset"]} · price {raw[x["asset_id"]]} · have {x["quantity"]}'] = (x, raw[x["asset_id"]])

        if sopts:
            sl = st.selectbox("Asset to sell", list(sopts.keys()))
            x, unit = sopts[sl]
            sq = st.number_input("Sell quantity", 1, max_value=int(x["quantity"]), step=1)
            st.metric("You receive", unit * int(sq), "Credits")
            disabled = (not trader or game["game_status"] != "running" or not game["market_open"])
            if st.button("💰 SELL", type="primary", use_container_width=True, disabled=disabled):
                try:
                    require_trader(team_id)
                    rpc("nexus_sell_to_market", {
                        "p_game_id": game_id,
                        "p_team_id": team_id,
                        "p_asset_code": x["code"],
                        "p_quantity": int(sq)
                    })
                    set_flash("market", f"Đã bán và nhận {unit * int(sq)} Credits.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.info("Không có asset để bán.")

    with tabs[4]:
        st.markdown("### 🕳️ Black Market Auction")
        st.caption(
            "Chợ đen chỉ hoạt động ở P2–P3. GV công bố một lượng Resource/Skill giới hạn. "
            "Mỗi team gửi số lượng muốn mua và giá bid trên MỖI UNIT. Bid của các team khác là bí mật."
        )
        if int(game["current_period"]) not in (2, 3):
            st.info("Black Market chỉ xuất hiện trong Period 2 và Period 3.")
        elif game["game_status"] != "running" or not game["market_open"]:
            st.info("Black Market hiện đang đóng cùng Market.")
        else:
            lots = [x for x in get_black_market_lots(game_id, game["current_period"]) if x.get("status") == "open"]
            if not lots:
                st.info("GV chưa mở lô hàng Black Market nào trong period này.")
            for lot in lots:
                asset = by_id[lot["asset_id"]]
                st.markdown(
                    f'#### {asset.get("emoji","")} {asset["name"]} · Supply remaining: '
                    f'**{lot["quantity_remaining"]}/{lot["quantity_total"]}**'
                )
                if lot.get("note"):
                    st.caption(lot["note"])
                mine = [b for b in get_black_market_bids(lot["id"]) if b["team_id"] == team_id]
                mine = mine[0] if mine else None
                if mine:
                    if mine["status"] == "approved":
                        st.success(
                            f'Bid APPROVED · {mine["approved_quantity"]} unit(s) × '
                            f'{mine["bid_price_per_unit"]} = '
                            f'{int(mine["approved_quantity"])*int(mine["bid_price_per_unit"])} Credits'
                        )
                    elif mine["status"] == "pending":
                        st.info(
                            f'Current bid: {mine["quantity_requested"]} unit(s) × '
                            f'{mine["bid_price_per_unit"]} Credits/unit · Waiting for teacher decision.'
                        )
                    elif mine["status"] == "rejected":
                        st.warning("Previous bid was rejected. You may submit a new bid while the lot remains open.")

                with st.form(f'bm_bid_{lot["id"]}'):
                    default_q = int(mine["quantity_requested"]) if mine and mine["status"] != "approved" else 1
                    default_p = int(mine["bid_price_per_unit"]) if mine and mine["status"] != "approved" else 1
                    c1, c2 = st.columns(2)
                    qty_bid = c1.number_input("Quantity wanted", min_value=1, value=max(1, default_q), step=1, key=f'bmq_{lot["id"]}')
                    price_bid = c2.number_input("Bid price / unit", min_value=1, value=max(1, default_p), step=1, key=f'bmp_{lot["id"]}')
                    st.caption(f'Maximum commitment if fully approved: {int(qty_bid)*int(price_bid)} Credits')
                    submit = st.form_submit_button(
                        "🔨 Submit / Update Bid",
                        type="primary",
                        use_container_width=True,
                        disabled=(not trader or (mine is not None and mine.get("status") == "approved"))
                    )
                if submit:
                    try:
                        require_trader(team_id)
                        rpc("nexus_submit_black_market_bid", {
                            "p_team_id": team_id,
                            "p_lot_id": lot["id"],
                            "p_quantity": int(qty_bid),
                            "p_price_per_unit": int(price_bid)
                        })
                        set_flash("market", f'Black Market bid submitted: {int(qty_bid)} × {int(price_bid)} Credits/unit.')
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with tabs[5]:
        tx = (
            q("nexus_transactions").select("*").eq("game_id", game_id)
            .or_(f"proposer_team_id.eq.{team_id},counterparty_team_id.eq.{team_id}")
            .order("created_at", desc=True).execute().data
        )
        st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)

# =========================
# TEACHER
# =========================
else:
    game_id = game_selector(include_test=True)
    pin = st.text_input("Teacher PIN", type="password")
    if pin != ADMIN_PIN:
        st.info("Enter Teacher PIN.")
        st.stop()

    game = get_game(game_id)
    st.markdown(
        f'<div class="team-banner"><div class="team-title">🎛️ Teacher Dashboard · {game["name"]}</div>'
        f'<div class="team-sub">Status {game["game_status"].upper()} · Period {game["current_period"]}</div></div>',
        unsafe_allow_html=True
    )
    render_period_card(game["current_period"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", game["game_status"].upper())
    c2.metric("Period", game["current_period"])
    c3.metric("Market", "OPEN" if game["market_open"] else "CLOSED")
    c4.metric("Public Display", "LIVE 📡" if game.get("public_visible") else "Hidden")

    with st.container(border=True):
        st.markdown("### 📡 Public Market Display")
        st.caption(
            "Chỉ MỘT lớp được hiển thị trên Public Market tại một thời điểm. "
            "Sinh viên ở màn Public sẽ không thấy danh sách các lớp khác."
        )
        if game.get("public_visible"):
            st.success(f'{game["name"]} đang được hiển thị trên Public Market.')
        else:
            if st.button("📡 Show this class on Public Market", type="primary", use_container_width=True):
                try:
                    set_public_game(game_id)
                    st.cache_data.clear()
                    set_flash("profile", f'Public Market đã chuyển sang {game["name"]}.')
                    st.rerun()
                except Exception as e:
                    st.error(f"Không thể đổi Public Market: {e}")

    if game["game_status"] == "setup":
        st.success("SETUP MODE: sinh viên có thể login, nhập tên và đọc mission; chưa thể giao dịch.")
        if st.button("🚀 START PERIOD 1", type="primary", use_container_width=True):
            rpc("nexus_start_game", {"p_game_id": game_id})
            set_flash("period", "Game bắt đầu. International Market và Trade Desk đã mở.", 1)
            st.rerun()

    elif game["game_status"] == "running":
        a, b, c = st.columns(3)
        if a.button("🟢 Open Market", disabled=game["market_open"], use_container_width=True):
            rpc("nexus_set_market_open", {"p_game_id": game_id, "p_open": True})
            st.rerun()
        if b.button("🔴 Close Market", disabled=not game["market_open"], use_container_width=True):
            rpc("nexus_set_market_open", {"p_game_id": game_id, "p_open": False})
            st.rerun()

        if int(game["current_period"]) < 4:
            is_final_step = int(game["current_period"]) == 3
            if c.button(
                "🏁 FINAL REVEAL P4" if is_final_step else "⏭️ Advance Period",
                disabled=game["market_open"],
                use_container_width=True,
                help=(
                    "Close Market first. P3→P4 immediately closes all trading and calculates Final Wealth."
                    if is_final_step
                    else "Close Market first. Advancing adds +1 specialization token/team and keeps market closed."
                )
            ):
                r = rpc("nexus_advance_period", {"p_game_id": game_id})
                newp = int(r["new_period"])
                if bool(r.get("final_reveal")):
                    set_flash(
                        "period",
                        "P4 đã được công bố. Không cộng token mới; mọi Trade / Build / Sell kết thúc và Final Wealth được chốt.",
                        4
                    )
                else:
                    set_flash(
                        "period",
                        "Đã cộng +1 token chuyên môn cho mỗi team. Đọc bối cảnh rồi mở Market.",
                        newp
                    )
                st.rerun()
        else:
            st.info("P4 là FINAL REVEAL. Không có vòng giao dịch P4.")

    teams = q("nexus_teams").select("*").eq("game_id", game_id).order("team_no").execute().data
    _, by_id, _ = get_assets()

    with st.expander("🕳️ Black Market Control", expanded=int(game["current_period"]) in (2, 3)):
        st.caption(
            "Preset Black Market lots are already configured for each class. "
            "During P2–P3, select a preset lot, open bidding, review ranked bids, then approve or reject sales. "
            "Custom lots are available only under Advanced / Emergency Supply."
        )

        lots_all = get_black_market_lots(game_id)

        st.markdown("### 📦 Preset Black Market Lots")
        if not lots_all:
            st.info("No preset Black Market lots are available for this server.")
        else:
            # Put current-period lots first, then future/other-period lots.
            lots_all = sorted(
                lots_all,
                key=lambda x: (
                    0 if int(x["period"]) == int(game["current_period"]) else 1,
                    int(x["period"]),
                    by_id[x["asset_id"]]["name"]
                )
            )

            lot_opts = {}
            for lot in lots_all:
                aa = by_id[lot["asset_id"]]
                current_tag = " · CURRENT" if int(lot["period"]) == int(game["current_period"]) else ""
                lot_opts[
                    f'P{lot["period"]} · {aa.get("emoji","")} {aa["name"]} · '
                    f'{lot["quantity_remaining"]}/{lot["quantity_total"]} left · {lot["status"].upper()}{current_tag}'
                ] = lot["id"]

            lot_label = st.selectbox(
                "Select preset lot",
                list(lot_opts.keys()),
                key="bm_manage_lot"
            )
            lot_id = lot_opts[lot_label]
            lot = next(x for x in lots_all if x["id"] == lot_id)
            aa = by_id[lot["asset_id"]]

            info1, info2, info3, info4 = st.columns(4)
            info1.metric("Period", f'P{lot["period"]}')
            info2.metric("Asset", aa["name"])
            info3.metric("Supply left", f'{lot["quantity_remaining"]}/{lot["quantity_total"]}')
            info4.metric("Status", str(lot["status"]).upper())

            if lot.get("note"):
                st.caption(f'📝 {lot["note"]}')

            s1, s2, s3 = st.columns(3)
            can_open = (
                int(game["current_period"]) == int(lot["period"])
                and int(lot["period"]) in (2, 3)
                and game["game_status"] == "running"
                and int(lot["quantity_remaining"]) > 0
            )
            if s1.button(
                "🟢 Open bidding",
                disabled=lot["status"] == "open" or not can_open,
                use_container_width=True
            ):
                q("nexus_black_market_lots").update({"status": "open"}).eq("id", lot_id).execute()
                st.rerun()

            if s2.button(
                "🔴 Close bidding",
                disabled=lot["status"] == "closed",
                use_container_width=True
            ):
                q("nexus_black_market_lots").update({"status": "closed"}).eq("id", lot_id).execute()
                st.rerun()

            if s3.button(
                "📝 Return to draft",
                disabled=lot["status"] == "draft",
                use_container_width=True
            ):
                q("nexus_black_market_lots").update({"status": "draft"}).eq("id", lot_id).execute()
                st.rerun()

            bids = get_black_market_bids(lot_id)
            suggestions = black_market_suggestions(lot, bids)
            suggestion_by_id = {x["id"]: x for x in suggestions}
            rows = []
            for b in bids:
                sugg = suggestion_by_id.get(b["id"], {})
                rows.append({
                    "Rank": sugg.get("rank", ""),
                    "Team": team_name(b["team_id"]),
                    "Qty wanted": b["quantity_requested"],
                    "Bid / unit": b["bid_price_per_unit"],
                    "Max total": int(b["quantity_requested"]) * int(b["bid_price_per_unit"]),
                    "Suggested qty": sugg.get("suggested_quantity", ""),
                    "Suggested cost": sugg.get("suggested_cost", ""),
                    "Status": b["status"],
                    "Approved qty": b["approved_quantity"]
                })

            if rows:
                st.markdown(f'#### 📊 Bids for {aa.get("emoji","")} {aa["name"]}')
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.caption(
                    "Server suggestion: highest bid price per unit first; ties go to the earlier bid. "
                    "Suggested allocation is advisory only — Teacher makes the final decision."
                )

                pending = [b for b in bids if b["status"] == "pending"]
                if pending:
                    bid_opts = {
                        f'{team_name(b["team_id"])} · {b["quantity_requested"]} × {b["bid_price_per_unit"]}/unit':
                        b["id"] for b in pending
                    }
                    bid_label = st.selectbox(
                        "Teacher decision",
                        list(bid_opts.keys()),
                        key="bm_teacher_bid"
                    )
                    bid_id = bid_opts[bid_label]
                    bid = next(b for b in pending if b["id"] == bid_id)
                    suggested = int(suggestion_by_id.get(bid_id, {}).get("suggested_quantity", 0))
                    max_approve = min(
                        int(bid["quantity_requested"]),
                        int(lot["quantity_remaining"])
                    )

                    if max_approve > 0:
                        approved_qty = st.number_input(
                            "Quantity to approve",
                            min_value=1,
                            max_value=max_approve,
                            value=max(1, suggested) if suggested > 0 else 1,
                            step=1,
                            key="bm_approve_qty"
                        )
                        st.metric(
                            "Charge to team",
                            int(approved_qty) * int(bid["bid_price_per_unit"]),
                            "Credits"
                        )

                        d1, d2 = st.columns(2)
                        if d1.button("✅ Approve sale", type="primary", use_container_width=True):
                            try:
                                r = rpc("nexus_approve_black_market_bid", {
                                    "p_bid_id": bid_id,
                                    "p_approved_quantity": int(approved_qty)
                                })
                                st.success(
                                    f'Approved {r["quantity"]} unit(s) at '
                                    f'{r["unit_price"]}/unit · total {r["total_cost"]} Credits.'
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                        if d2.button("❌ Reject bid", use_container_width=True):
                            try:
                                rpc("nexus_reject_black_market_bid", {"p_bid_id": bid_id})
                                st.warning("Bid rejected.")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    else:
                        st.warning("No supply remains for approval.")
                else:
                    st.info("No pending bids remain for this lot.")
            else:
                st.info("No bids yet for this lot.")

        with st.expander("⚙️ Advanced / Emergency Supply", expanded=False):
            st.caption(
                "Optional teacher tool. Use this only if you intentionally want to inject extra supply "
                "beyond the preset Black Market lots."
            )
            bm_assets = [a for a in get_assets()[0] if a["category"] in ("resource", "skill")]
            bm_asset_opts = {
                f'{a.get("emoji","")} {a["name"]} · {a["category"]}': a["id"]
                for a in bm_assets
            }

            with st.form("create_black_market_lot"):
                c1, c2, c3 = st.columns(3)
                bm_period = c1.selectbox(
                    "Period",
                    [2, 3],
                    index=0 if int(game["current_period"]) != 3 else 1
                )
                bm_asset_label = c2.selectbox(
                    "Resource / Skill",
                    list(bm_asset_opts.keys())
                )
                bm_qty = c3.number_input(
                    "Supply quantity",
                    min_value=1,
                    value=1,
                    step=1
                )
                bm_note = st.text_input(
                    "Optional note",
                    placeholder="e.g. Emergency shipment / scarce import batch"
                )
                create_lot = st.form_submit_button(
                    "➕ Create Custom Black Market Lot",
                    use_container_width=True
                )

            if create_lot:
                q("nexus_black_market_lots").insert({
                    "game_id": game_id,
                    "period": int(bm_period),
                    "asset_id": bm_asset_opts[bm_asset_label],
                    "quantity_total": int(bm_qty),
                    "quantity_remaining": int(bm_qty),
                    "status": "draft",
                    "note": bm_note.strip() or "Custom / Emergency Supply"
                }).execute()
                st.success("Custom Black Market lot created as DRAFT.")
                st.rerun()

    st.markdown("### 👥 Team Monitor")
    monitor = []
    for t in teams:
        monitor.append({
            "Team": t["team_name"],
            "Specialisation": by_id[t["specialization_asset_id"]]["name"],
            "Members": ", ".join(m["full_name"] for m in get_members(t["id"])),
            "Cash": t["cash"],
            "Asset units": sum(x["quantity"] for x in get_inventory(t["id"]))
        })
    st.dataframe(pd.DataFrame(monitor), use_container_width=True, hide_index=True)

    with st.expander("🧪 Team Login Visibility"):
        st.caption(
            "Cho phép server thử nghiệm xuất hiện hoặc biến mất khỏi danh sách Team Login. "
            "Public Market được điều khiển riêng bằng mục 📡 Public Market Display."
        )
        if game.get("team_login_visible", True):
            if st.button("🙈 Hide this server from Team Login", use_container_width=True):
                q("nexus_games").update({"team_login_visible": False}).eq("id", game_id).execute()
                st.cache_data.clear()
                st.rerun()
        else:
            if st.button("👁️ Show this server in Team Login", use_container_width=True):
                q("nexus_games").update({"team_login_visible": True}).eq("id", game_id).execute()
                st.cache_data.clear()
                st.rerun()

    with st.expander("🔐 Team Codes & Trader Device Control"):
        topts = {t["team_name"]: t["id"] for t in teams}
        selected = st.selectbox("Team", list(topts.keys()), key="ctl_team")
        sid = topts[selected]
        c1, c2, c3 = st.columns(3)

        if c1.button("Reset Trader Device", use_container_width=True):
            rpc("nexus_reset_trader_device", {"p_team_id": sid})
            st.success("Trader Device lock reset. Team can claim a new device.")

        if c2.button("Generate new Team Login Code", use_container_width=True):
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            code = "L-" + "".join(secrets.choice(alphabet) for _ in range(6))
            rpc("nexus_set_login_code", {"p_team_id": sid, "p_new_code": code})
            st.session_state["_new_code"] = f"{selected} NEW LOGIN CODE: {code}"

        if c3.button("Generate new Trader Code", use_container_width=True):
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            code = "T-" + "".join(secrets.choice(alphabet) for _ in range(6))
            rpc("nexus_set_trader_code", {"p_team_id": sid, "p_new_code": code})
            st.session_state["_new_code"] = f"{selected} NEW TRADER CODE: {code}"

        if st.session_state.get("_new_code"):
            st.warning(st.session_state["_new_code"] + " · Mã này chỉ hiển thị trong phiên hiện tại, hãy copy ngay.")

    with st.expander("↩️ Corrections / Undo"):
        st.caption("Reverse không xóa lịch sử; hệ thống tạo bút toán đảo ngược. Nếu bên nhận đã tiêu tài sản/tiền, reverse sẽ bị chặn.")
        txs = (
            q("nexus_transactions").select("*").eq("game_id", game_id)
            .eq("status", "completed").eq("reversed", False)
            .order("created_at", desc=True).limit(100).execute().data
        )
        tx_opts = {}
        for x in txs:
            if x["transaction_type"] == "system_adjustment":
                continue
            label = f'{x["period"]} · {x["transaction_type"]} · {team_name(x["proposer_team_id"]) if x["proposer_team_id"] else "Market"} · {x["id"][:8]}'
            tx_opts[label] = x["id"]

        if tx_opts:
            txsel = st.selectbox("Completed transaction", list(tx_opts.keys()))
            if st.button("Reverse selected transaction"):
                try:
                    rpc("nexus_reverse_transaction", {"p_transaction_id": tx_opts[txsel]})
                    st.success("Transaction reversed.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        builds = (
            q("nexus_builds").select("*").eq("game_id", game_id).eq("reversed", False)
            .order("created_at", desc=True).limit(100).execute().data
        )
        if builds:
            bopts = {f'P{b["period"]} · {team_name(b["team_id"])} · build {b["id"][:8]}': b["id"] for b in builds}
            bsel = st.selectbox("Build record", list(bopts.keys()))
            if st.button("Reverse selected build"):
                try:
                    rpc("nexus_reverse_build", {"p_build_id": bopts[bsel]})
                    st.success("Build reversed.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    if game["game_status"] == "ended":
        st.markdown("## 🏆 FINAL RANKING — TEACHER ONLY")
        scores = q("nexus_final_scores").select("*").eq("game_id", game_id).order("final_rank").execute().data
        rank = []
        for s in scores:
            m = get_mission(s["team_id"])
            rank.append({
                "Rank": s["final_rank"], "Team": team_name(s["team_id"]),
                "Base Wealth": s["base_wealth"], "Mission": m["title"] if m else "",
                "Metric": s["mission_metric"], "Mission Level": int(s["mission_multiplier"]),
                "Bonus": s["mission_bonus"], "Final Wealth": s["final_wealth"]
            })
        st.dataframe(pd.DataFrame(rank), use_container_width=True, hide_index=True)

    st.markdown("### 📦 Export")
    data = export_game_xlsx(game_id)
    safe = (game.get("class_label") or "game").replace(" ", "_")
    st.download_button(
        "⬇️ Download Full Game Data (.xlsx)",
        data=data,
        file_name=f"NEXUS_{safe}_full_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    with st.expander("♻️ Reset Server for New Class", expanded=False):
        st.error(
            "DANGER ZONE · Reset sẽ xóa toàn bộ dữ liệu của phiên chơi hiện tại trên server này. "
            "Hãy Export file .xlsx trước khi reset."
        )
        st.caption(
            "GIỮ NGUYÊN: Team Login Code, Trader Device Code, số team, specialisation, "
            "Secret Mission assignment, bảng giá và Preset Black Market lots.\n\n"
            "RESET: P1/SETUP, Market closed, Cash & inventory ban đầu, member names, "
            "Trader Device claims, trades, builds, Black Market bids, mission rewards và final scores."
        )

        reset_export_confirm = st.checkbox(
            "Tôi xác nhận đã tải Full Game Data (.xlsx) nếu cần lưu dữ liệu lớp vừa chơi.",
            key=f"reset_export_confirm_{game_id}"
        )
        reset_word = st.text_input(
            'Gõ chính xác "RESET" để xác nhận',
            key=f"reset_word_{game_id}"
        )

        can_reset = reset_export_confirm and reset_word.strip().upper() == "RESET"
        if st.button(
            "♻️ RESET THIS SERVER FOR NEW CLASS",
            type="primary",
            use_container_width=True,
            disabled=not can_reset,
            key=f"reset_game_{game_id}"
        ):
            try:
                result = rpc("nexus_reset_game_for_new_class", {"p_game_id": game_id})
                st.cache_data.clear()
                for k in list(st.session_state.keys()):
                    if k.startswith(("reset_export_confirm_", "reset_word_")):
                        del st.session_state[k]
                set_flash(
                    "profile",
                    f'Server đã reset: {result.get("teams", 0)} teams · '
                    f'{result.get("starting_cash", 0)} Credits · '
                    f'{result.get("starting_tokens", 0)} tokens/team.'
                )
                st.rerun()
            except Exception as e:
                st.error(f"Reset failed: {e}")
