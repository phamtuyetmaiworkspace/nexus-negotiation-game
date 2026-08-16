
import random
import streamlit as st
from supabase import create_client, Client
import pandas as pd

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

# -------------------- VISUAL THEME --------------------
st.markdown(
    """
    <style>
    :root {
        --nexus-primary: #5B5FEF;
        --nexus-secondary: #8B5CF6;
        --nexus-cyan: #06B6D4;
        --nexus-dark: #171A2B;
        --nexus-muted: #667085;
        --nexus-bg: #F7F8FC;
        --resource: #0F9D75;
        --skill: #7C3AED;
        --item: #D97706;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 0%, rgba(91,95,239,.08), transparent 30%),
            radial-gradient(circle at 90% 10%, rgba(6,182,212,.08), transparent 25%),
            #F7F8FC;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F1F2FF 0%, #F8FAFF 100%);
        border-right: 1px solid rgba(91,95,239,.12);
    }

    .nexus-hero {
        padding: 22px 26px;
        border-radius: 22px;
        background: linear-gradient(135deg, #25275A 0%, #5B5FEF 55%, #06B6D4 120%);
        color: white;
        box-shadow: 0 14px 40px rgba(35,40,110,.18);
        margin-bottom: 18px;
    }

    .nexus-hero h1 {
        margin: 0;
        font-size: 2.25rem;
        letter-spacing: -.03em;
    }

    .nexus-hero p {
        margin: 6px 0 0 0;
        opacity: .88;
        font-size: 1rem;
    }

    .team-banner {
        padding: 18px 22px;
        border-radius: 18px;
        background: white;
        border: 1px solid rgba(91,95,239,.12);
        box-shadow: 0 8px 24px rgba(40,44,90,.08);
        margin-bottom: 10px;
    }

    .team-title {
        font-size: 1.55rem;
        font-weight: 800;
        color: #24264D;
        margin: 0;
    }

    .team-subtitle {
        color: #667085;
        margin-top: 4px;
    }

    .mission-card {
        padding: 18px 20px;
        border-radius: 18px;
        background: linear-gradient(135deg, #FFF8E6 0%, #FFF1C6 100%);
        border: 1px solid #F5D47B;
        box-shadow: 0 8px 24px rgba(140,104,20,.08);
        margin: 8px 0 16px 0;
    }

    .mission-title {
        font-weight: 800;
        color: #7A4E00;
        font-size: 1.1rem;
    }

    .mission-text {
        color: #6B571F;
        margin-top: 5px;
        line-height: 1.5;
    }

    .asset-card {
        background: white;
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 6px 18px rgba(40,44,90,.07);
        border: 1px solid #EAECF5;
        min-height: 112px;
        margin-bottom: 10px;
    }

    .asset-card.resource { border-top: 4px solid var(--resource); }
    .asset-card.skill { border-top: 4px solid var(--skill); }
    .asset-card.item { border-top: 4px solid var(--item); }

    .asset-name {
        font-weight: 750;
        color: #25284A;
        margin-bottom: 8px;
    }

    .asset-qty {
        font-size: 1.75rem;
        font-weight: 850;
        color: #171A2B;
    }

    .asset-type {
        color: #98A2B3;
        text-transform: uppercase;
        font-size: .72rem;
        letter-spacing: .08em;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #EAECF5;
        padding: 13px 15px;
        border-radius: 16px;
        box-shadow: 0 5px 16px rgba(40,44,90,.055);
    }

    div[data-testid="stMetricValue"] {
        color: #2E326F;
        font-weight: 800;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        min-height: 42px;
        transition: all .18s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(91,95,239,.14);
    }

    div[data-testid="stTabs"] button {
        font-weight: 700;
    }

    .live-note {
        color: #667085;
        font-size: .86rem;
    }

    .success-pop {
        padding: 14px 18px;
        background: linear-gradient(135deg, #E7FFF4, #F0FFFA);
        border: 1px solid #78DDB4;
        border-radius: 14px;
        color: #116443;
        font-weight: 750;
        animation: popin .35s ease-out;
        margin-bottom: 12px;
    }

    @keyframes popin {
        0% { transform: scale(.96); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- DB HELPERS --------------------
def q(table):
    return sb.table(table)

def rpc(name, params):
    return sb.rpc(name, params).execute().data

@st.cache_data(ttl=20)
def get_games():
    return (
        q("nexus_games")
        .select("id,name,class_label,current_period,market_open")
        .order("created_at", desc=True)
        .execute()
        .data
    )

@st.cache_data(ttl=20)
def get_assets():
    rows = (
        q("nexus_assets")
        .select("id,code,name,category,emoji")
        .eq("active", True)
        .execute()
        .data
    )
    by_id = {r["id"]: r for r in rows}
    by_code = {r["code"]: r for r in rows}
    return rows, by_id, by_code

def get_game(game_id):
    return q("nexus_games").select("*").eq("id", game_id).single().execute().data

def get_team(team_id):
    return q("nexus_teams").select("*").eq("id", team_id).single().execute().data

def get_members(team_id):
    return (
        q("nexus_members")
        .select("full_name,display_order")
        .eq("team_id", team_id)
        .order("display_order")
        .execute()
        .data
    )

def save_members(team_id, names):
    clean = [n.strip() for n in names if n.strip()]
    q("nexus_members").delete().eq("team_id", team_id).execute()
    if clean:
        q("nexus_members").insert([
            {"team_id": team_id, "full_name": name, "display_order": i + 1}
            for i, name in enumerate(clean)
        ]).execute()

def get_secret_mission(team_id):
    team = get_team(team_id)
    mission_id = team.get("secret_mission_id")
    if not mission_id:
        return None
    rows = (
        q("nexus_secret_missions")
        .select("id,code,title,description,bonus_type,bonus_value")
        .eq("id", mission_id)
        .execute()
        .data
    )
    return rows[0] if rows else None

def get_inventory(team_id):
    _, by_id, _ = get_assets()
    rows = (
        q("nexus_inventory")
        .select("asset_id,quantity")
        .eq("team_id", team_id)
        .gt("quantity", 0)
        .execute()
        .data
    )
    out = []
    for r in rows:
        a = by_id.get(r["asset_id"], {})
        out.append({
            "asset_id": r["asset_id"],
            "code": a.get("code"),
            "asset": f'{a.get("emoji","")} {a.get("name","")}'.strip(),
            "name": a.get("name", ""),
            "emoji": a.get("emoji", ""),
            "category": a.get("category"),
            "quantity": r["quantity"],
        })
    return sorted(out, key=lambda x: (x["category"], x["name"]))

def get_directory(game_id):
    teams = (
        q("nexus_teams")
        .select("id,team_no,team_name,specialization_asset_id")
        .eq("game_id", game_id)
        .order("team_no")
        .execute()
        .data
    )
    _, by_id, _ = get_assets()
    rows = []
    for t in teams:
        members = get_members(t["id"])
        a = by_id.get(t["specialization_asset_id"], {})
        rows.append({
            "Team": t["team_name"],
            "Specialisation": f'{a.get("emoji","")} {a.get("name","")}'.strip(),
            "Members": ", ".join(m["full_name"] for m in members),
        })
    return rows

def get_market_prices(game_id, period):
    _, by_id, _ = get_assets()
    rows = (
        q("nexus_market_prices")
        .select("asset_id,buy_price")
        .eq("game_id", game_id)
        .eq("period", period)
        .execute()
        .data
    )
    out = []
    for r in rows:
        a = by_id.get(r["asset_id"], {})
        out.append({
            "Asset": f'{a.get("emoji","")} {a.get("name","")}'.strip(),
            "Category": a.get("category", ""),
            "International Market": r["buy_price"],
        })
    order = {"resource": 0, "skill": 1, "item": 2}
    return sorted(out, key=lambda x: (order.get(x["Category"], 9), x["Asset"]))

def verify_team(game_id, team_no, pin):
    return rpc("nexus_verify_team_pin", {
        "p_game_id": game_id,
        "p_team_no": int(team_no),
        "p_pin": str(pin),
    })

def team_name(team_id):
    return get_team(team_id)["team_name"]

def get_pending_for_team(team_id):
    return (
        q("nexus_transactions")
        .select("*")
        .eq("counterparty_team_id", team_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
        .data
    )

def get_latest_completed_trade(team_id, game_id):
    rows = (
        q("nexus_transactions")
        .select("id,completed_at")
        .eq("game_id", game_id)
        .eq("status", "completed")
        .or_(f"proposer_team_id.eq.{team_id},counterparty_team_id.eq.{team_id}")
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None

def describe_transaction(tx):
    _, by_id, _ = get_assets()
    lines = (
        q("nexus_transaction_lines")
        .select("*")
        .eq("transaction_id", tx["id"])
        .execute()
        .data
    )
    proposer_gives, counter_gives = [], []
    for line in lines:
        if line["asset_id"]:
            a = by_id.get(line["asset_id"], {})
            text = f'{line["quantity"]} × {a.get("emoji","")} {a.get("name","")}'.strip()
        else:
            text = f'{line["credits"]} Credits'
        if line["from_team_id"] == tx["proposer_team_id"]:
            proposer_gives.append(text)
        else:
            counter_gives.append(text)
    return " + ".join(proposer_gives), " + ".join(counter_gives)

def set_flash(kind, message):
    st.session_state["_nexus_flash"] = {"kind": kind, "message": message}

def render_flash():
    event = st.session_state.pop("_nexus_flash", None)
    if not event:
        return
    st.markdown(
        f'<div class="success-pop">✨ {event["message"]}</div>',
        unsafe_allow_html=True,
    )
    st.toast(event["message"], icon="✅")
    if event["kind"] in ("trade", "build"):
        st.balloons()

def render_inventory_cards(items):
    if not items:
        st.info("Chưa có tài sản.")
        return
    for start in range(0, len(items), 4):
        cols = st.columns(4)
        for col, item in zip(cols, items[start:start+4]):
            with col:
                st.markdown(
                    f"""
                    <div class="asset-card {item['category']}">
                        <div class="asset-type">{item['category']}</div>
                        <div class="asset-name">{item['emoji']} {item['name']}</div>
                        <div class="asset-qty">× {item['quantity']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

def assign_balanced_missions(game_id):
    teams = (
        q("nexus_teams")
        .select("id,team_no")
        .eq("game_id", game_id)
        .order("team_no")
        .execute()
        .data
    )
    missions = (
        q("nexus_secret_missions")
        .select("id,title")
        .order("code")
        .execute()
        .data
    )
    if not teams or not missions:
        return 0
    mission_ids = [m["id"] for m in missions]
    random.shuffle(mission_ids)
    assigned = 0
    for idx, team in enumerate(teams):
        if idx > 0 and idx % len(mission_ids) == 0:
            random.shuffle(mission_ids)
        mission_id = mission_ids[idx % len(mission_ids)]
        (
            q("nexus_teams")
            .update({
                "secret_mission_id": mission_id,
                "mission_completed": False,
                "mission_bonus_awarded": 0,
            })
            .eq("id", team["id"])
            .execute()
        )
        assigned += 1
    return assigned

@st.fragment(run_every="3s")
def live_trader_status(team_id, game_id):
    fresh_team = get_team(team_id)
    fresh_game = get_game(game_id)
    pending = get_pending_for_team(team_id)

    latest = get_latest_completed_trade(team_id, game_id)
    latest_id = latest["id"] if latest else None
    if "_last_completed_trade" not in st.session_state:
        st.session_state["_last_completed_trade"] = latest_id
    elif latest_id and latest_id != st.session_state["_last_completed_trade"]:
        st.session_state["_last_completed_trade"] = latest_id
        set_flash("trade", "Giao dịch vừa được hoàn tất!")
        st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Cash", fresh_team["cash"])
    c2.metric("🕰️ Period", fresh_game["current_period"])
    c3.metric("📨 Offers", len(pending))
    c4.metric("Market", "OPEN 🟢" if fresh_game["market_open"] else "CLOSED 🔴")

    if not pending:
        st.markdown(
            '<div class="live-note">📡 Live Inbox đang tự kiểm tra offer mới mỗi 3 giây.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown("### 📨 Live Inbox")
    for tx in pending:
        proposer = team_name(tx["proposer_team_id"])
        proposer_gives, counter_gives = describe_transaction(tx)

        with st.container(border=True):
            st.markdown(f"**{proposer} gửi đề nghị**")
            c_left, c_mid, c_right = st.columns([1, .25, 1])
            c_left.info(f"Họ đưa\n\n**{proposer_gives}**")
            c_mid.markdown("<h2 style='text-align:center'>⇄</h2>", unsafe_allow_html=True)
            c_right.warning(f"Bạn đưa\n\n**{counter_gives}**")

            c_accept, c_reject = st.columns(2)
            if c_accept.button(
                "🤝 Accept",
                key=f'live_acc_{tx["id"]}',
                type="primary",
                use_container_width=True,
                disabled=not fresh_game["market_open"],
            ):
                try:
                    rpc("nexus_accept_trade", {
                        "p_transaction_id": tx["id"],
                        "p_accepting_team_id": team_id,
                    })
                    st.session_state["_last_completed_trade"] = tx["id"]
                    set_flash("trade", "Giao dịch thành công! Tài sản đã được chuyển.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            if c_reject.button(
                "Reject",
                key=f'live_rej_{tx["id"]}',
                use_container_width=True,
            ):
                try:
                    rpc("nexus_reject_trade", {
                        "p_transaction_id": tx["id"],
                        "p_rejecting_team_id": team_id,
                    })
                    st.toast("Đã từ chối offer.", icon="✖️")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

def current_game_selector(label="Game session"):
    games = get_games()
    if not games:
        st.error("No game session exists.")
        st.stop()
    opts = {
        f'{g["name"]} ({g.get("class_label") or "no class label"})': g["id"]
        for g in games
    }
    chosen = st.selectbox(label, list(opts.keys()))
    return opts[chosen]

# -------------------- HEADER --------------------
st.markdown(
    """
    <div class="nexus-hero">
        <h1>🧩 NEXUS</h1>
        <p>Four Eras Negotiation Game · Trade smart · Build value · Manage your BATNA</p>
    </div>
    """,
    unsafe_allow_html=True,
)

render_flash()

mode = st.sidebar.radio(
    "Mode",
    ["🌐 Public Market & Directory", "🤝 Team Trader", "🎛️ Teacher"],
)

# -------------------- PUBLIC --------------------
if mode == "🌐 Public Market & Directory":
    game_id = current_game_selector()
    game = get_game(game_id)

    st.markdown(
        f"""
        <div class="team-banner">
            <div class="team-title">{game["name"]} · Period {game["current_period"]}</div>
            <div class="team-subtitle">
                Market status: {"🟢 OPEN" if game["market_open"] else "🔴 CLOSED"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["💹 International Market", "👥 Team Directory"])
    with tab1:
        df = pd.DataFrame(get_market_prices(game_id, game["current_period"]))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("International Market là mức giá cố định của GV; giá Team-to-Team do hai bên tự thương lượng.")
    with tab2:
        st.dataframe(
            pd.DataFrame(get_directory(game_id)),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Tên thành viên do mỗi team tự cập nhật trong Team Trader.")

# -------------------- TEAM --------------------
elif mode == "🤝 Team Trader":
    if "team_id" not in st.session_state:
        st.markdown("## Team Login")
        game_id = current_game_selector()
        c1, c2 = st.columns(2)
        with c1:
            team_no = st.number_input("Team number", min_value=1, step=1)
        with c2:
            pin = st.text_input("Trader PIN", type="password")

        if st.button("Enter Team Control", type="primary", use_container_width=True):
            tid = verify_team(game_id, team_no, pin)
            if tid:
                st.session_state["team_id"] = tid
                st.session_state["game_id"] = game_id
                latest = get_latest_completed_trade(tid, game_id)
                st.session_state["_last_completed_trade"] = latest["id"] if latest else None
                st.rerun()
            else:
                st.error("Invalid Team number or Trader PIN.")
        st.stop()

    team_id = st.session_state["team_id"]
    game_id = st.session_state["game_id"]
    team = get_team(team_id)
    game = get_game(game_id)
    assets, by_id, by_code = get_assets()
    specialization = by_id.get(team["specialization_asset_id"], {})
    members = get_members(team_id)

    st.markdown(
        f"""
        <div class="team-banner">
            <div class="team-title">{team["team_name"]}</div>
            <div class="team-subtitle">
                {specialization.get("emoji","")} {specialization.get("name","")} ·
                {" · ".join(m["full_name"] for m in members) if members else "Chưa nhập thành viên"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_logout, _ = st.columns([1, 4])
    if c_logout.button("Log out"):
        st.session_state.clear()
        st.rerun()

    live_trader_status(team_id, game_id)

    tabs = st.tabs([
        "🏠 My Team",
        "🤝 Trade",
        "🛠️ Build",
        "🌍 International Market",
        "🧾 History",
    ])

    with tabs[0]:
        # SECRET MISSION
        mission = get_secret_mission(team_id)
        if mission:
            bonus = int(float(mission["bonus_value"]))
            st.markdown(
                f"""
                <div class="mission-card">
                    <div class="mission-title">🔒 SECRET MISSION · {mission["title"]}</div>
                    <div class="mission-text">{mission["description"]}</div>
                    <div class="mission-text"><b>Bonus: +{bonus} Wealth Points</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption("Chỉ team của bạn và GV nhìn thấy nhiệm vụ này.")
        else:
            st.info("🔒 GV chưa phân Secret Mission cho team này.")

        st.markdown("### 👥 Thành viên Team")
        current_names = "\n".join(m["full_name"] for m in members)
        with st.form("member_form"):
            member_text = st.text_area(
                "Nhập tên thành viên — mỗi dòng một người",
                value=current_names,
                height=140,
                placeholder="Nguyễn Văn A\nTrần Thị B\nLê Văn C",
            )
            save_member_btn = st.form_submit_button(
                "💾 Lưu tên thành viên",
                type="primary",
            )

        if save_member_btn:
            names = [x.strip() for x in member_text.splitlines() if x.strip()]
            if not (3 <= len(names) <= 6):
                st.error("Mỗi team nên có từ 3 đến 6 thành viên.")
            else:
                save_members(team_id, names)
                st.cache_data.clear()
                set_flash("profile", "Đã cập nhật tên thành viên.")
                st.rerun()

        st.markdown("### 🎒 Inventory")
        render_inventory_cards(get_inventory(team_id))

    with tabs[1]:
        st.markdown("### Create Trade Offer")
        directory = (
            q("nexus_teams")
            .select("id,team_no,team_name")
            .eq("game_id", game_id)
            .neq("id", team_id)
            .order("team_no")
            .execute()
            .data
        )
        team_opts = {t["team_name"]: t["id"] for t in directory}
        target_name = st.selectbox("Counterparty", list(team_opts.keys()))
        target_id = team_opts[target_name]

        st.caption("Giá Team-to-Team hoàn toàn do hai bên tự quyết định.")
        left, right = st.columns(2)

        with left:
            st.markdown("#### 📤 I GIVE")
            my_type = st.radio(
                "Loại",
                ["Asset", "Credits"],
                horizontal=True,
                key="mygive",
            )
            if my_type == "Asset":
                inv = [x for x in get_inventory(team_id) if x["quantity"] > 0]
                my_asset_opts = {
                    f'{x["asset"]} · bạn có {x["quantity"]}': x["code"]
                    for x in inv
                }
                if not my_asset_opts:
                    st.warning("Bạn không có asset để offer.")
                    my_payload = None
                else:
                    label = st.selectbox("Asset", list(my_asset_opts.keys()))
                    qty = st.number_input("Quantity", min_value=1, step=1)
                    my_payload = [{"asset_code": my_asset_opts[label], "quantity": int(qty)}]
            else:
                credits = st.number_input("Credits", min_value=1, step=1)
                my_payload = [{"credits": int(credits)}]

        with right:
            st.markdown("#### 📥 I REQUEST")
            their_type = st.radio(
                "Loại ",
                ["Asset", "Credits"],
                horizontal=True,
                key="theirgive",
            )
            if their_type == "Asset":
                asset_opts = {
                    f'{a["emoji"] or ""} {a["name"]}'.strip(): a["code"]
                    for a in assets
                }
                label2 = st.selectbox("Requested asset", list(asset_opts.keys()))
                qty2 = st.number_input("Requested quantity", min_value=1, step=1)
                their_payload = [{"asset_code": asset_opts[label2], "quantity": int(qty2)}]
            else:
                credits2 = st.number_input("Credits requested", min_value=1, step=1)
                their_payload = [{"credits": int(credits2)}]

        if st.button(
            "📨 Send Offer",
            type="primary",
            use_container_width=True,
            disabled=not game["market_open"] or my_payload is None,
        ):
            try:
                rpc("nexus_create_trade", {
                    "p_game_id": game_id,
                    "p_proposer_team_id": team_id,
                    "p_counterparty_team_id": target_id,
                    "p_period": int(game["current_period"]),
                    "p_proposer_gives": my_payload,
                    "p_counterparty_gives": their_payload,
                    "p_note": None,
                })
                st.toast("Offer đã được gửi!", icon="📨")
            except Exception as e:
                st.error(str(e))

    with tabs[2]:
        st.markdown("### 🛠️ Build Item")
        recipe_rows = q("nexus_recipes").select("*").execute().data
        opts = {}
        for r in recipe_rows:
            output = by_id[r["output_asset_id"]]
            resource = by_id[r["resource_asset_id"]]
            skill = by_id[r["skill_asset_id"]]
            label = (
                f'{output["emoji"] or ""} {output["name"]}'
                f'  ←  {resource["emoji"] or ""} {resource["name"]}'
                f' + {skill["emoji"] or ""} {skill["name"]}'
            )
            opts[label] = output["code"]

        build_choice = st.selectbox("Recipe", list(opts.keys()))
        build_qty = st.number_input(
            "Build quantity",
            min_value=1,
            step=1,
            key="build_qty",
        )

        if st.button(
            "✨ BUILD",
            type="primary",
            use_container_width=True,
            disabled=not game["market_open"],
        ):
            try:
                rpc("nexus_build_item", {
                    "p_game_id": game_id,
                    "p_team_id": team_id,
                    "p_output_asset_code": opts[build_choice],
                    "p_quantity": int(build_qty),
                })
                set_flash("build", f"Build thành công ×{int(build_qty)}!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with tabs[3]:
        st.markdown("### 🌍 Sell to International Market")
        inv = get_inventory(team_id)
        raw_prices = (
            q("nexus_market_prices")
            .select("asset_id,buy_price")
            .eq("game_id", game_id)
            .eq("period", game["current_period"])
            .execute()
            .data
        )
        raw_map = {r["asset_id"]: r["buy_price"] for r in raw_prices}
        price_map = {}
        for x in inv:
            if x["asset_id"] in raw_map:
                price_map[
                    f'{x["asset"]} · Market {raw_map[x["asset_id"]]} · bạn có {x["quantity"]}'
                ] = (x["code"], raw_map[x["asset_id"]], x["quantity"])

        if not price_map:
            st.info("Không có asset có thể bán.")
        else:
            sell_label = st.selectbox("Asset", list(price_map.keys()))
            sell_code, unit_price, owned_qty = price_map[sell_label]
            sell_qty = st.number_input(
                "Quantity to sell",
                min_value=1,
                max_value=int(owned_qty),
                step=1,
                key="sell_qty",
            )
            st.metric("You will receive", unit_price * int(sell_qty), "Credits")
            if st.button(
                "💰 SELL TO MARKET",
                type="primary",
                use_container_width=True,
                disabled=not game["market_open"],
            ):
                try:
                    result = rpc("nexus_sell_to_market", {
                        "p_game_id": game_id,
                        "p_team_id": team_id,
                        "p_asset_code": sell_code,
                        "p_quantity": int(sell_qty),
                    })
                    set_flash(
                        "market",
                        f"Đã bán thành công và nhận {unit_price * int(sell_qty)} Credits!",
                    )
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with tabs[4]:
        tx = (
            q("nexus_transactions")
            .select(
                "id,period,transaction_type,proposer_team_id,"
                "counterparty_team_id,status,created_at,completed_at,note"
            )
            .eq("game_id", game_id)
            .or_(f"proposer_team_id.eq.{team_id},counterparty_team_id.eq.{team_id}")
            .order("created_at", desc=True)
            .execute()
            .data
        )
        st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)

# -------------------- TEACHER --------------------
else:
    game_id = current_game_selector()
    admin_pin = st.text_input("Teacher PIN", type="password")
    if admin_pin != ADMIN_PIN:
        st.info("Enter the Teacher PIN.")
        st.stop()

    game = get_game(game_id)
    st.markdown(
        f"""
        <div class="team-banner">
            <div class="team-title">🎛️ Teacher Dashboard · {game["name"]}</div>
            <div class="team-subtitle">Control periods, market state and team missions.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Period", game["current_period"])
    c2.metric("Market", "OPEN" if game["market_open"] else "CLOSED")
    team_count = (
        q("nexus_teams")
        .select("id", count="exact")
        .eq("game_id", game_id)
        .execute()
        .count
    )
    c3.metric("Teams", team_count)

    a, b, c = st.columns(3)
    if a.button("🟢 Open Market", disabled=game["market_open"], use_container_width=True):
        rpc("nexus_set_market_open", {"p_game_id": game_id, "p_open": True})
        st.cache_data.clear()
        st.rerun()

    if b.button("🔴 Close Market", disabled=not game["market_open"], use_container_width=True):
        rpc("nexus_set_market_open", {"p_game_id": game_id, "p_open": False})
        st.cache_data.clear()
        st.rerun()

    if c.button(
        "⏭️ Advance Period",
        disabled=game["current_period"] >= 4,
        use_container_width=True,
    ):
        try:
            rpc("nexus_advance_period", {"p_game_id": game_id})
            st.cache_data.clear()
            set_flash("period", "Đã chuyển sang Period tiếp theo và cộng token chuyên môn.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    with st.expander("🔒 Secret Mission Control", expanded=False):
        st.caption("Mission được phân cân bằng và ngẫu nhiên. Chỉ nên shuffle trước khi game bắt đầu.")
        confirm_shuffle = st.checkbox("Tôi xác nhận muốn phân / phân lại nhiệm vụ.")
        if st.button(
            "🎯 Assign / Shuffle Secret Missions",
            disabled=not confirm_shuffle,
        ):
            count = assign_balanced_missions(game_id)
            set_flash("mission", f"Đã phân Secret Mission cho {count} team.")
            st.rerun()

        teams_for_mission = (
            q("nexus_teams")
            .select("id,team_no,team_name,secret_mission_id")
            .eq("game_id", game_id)
            .order("team_no")
            .execute()
            .data
        )
        mission_rows = (
            q("nexus_secret_missions")
            .select("id,title,description,bonus_value")
            .execute()
            .data
        )
        mission_map = {m["id"]: m for m in mission_rows}
        teacher_missions = []
        for t in teams_for_mission:
            m = mission_map.get(t.get("secret_mission_id"))
            teacher_missions.append({
                "Team": t["team_name"],
                "Mission": m["title"] if m else "Not assigned",
                "Bonus": int(float(m["bonus_value"])) if m else 0,
            })
        st.dataframe(
            pd.DataFrame(teacher_missions),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Team Monitor")
    teams = (
        q("nexus_teams")
        .select("id,team_no,team_name,cash,specialization_asset_id")
        .eq("game_id", game_id)
        .order("team_no")
        .execute()
        .data
    )
    _, by_id, _ = get_assets()
    monitor = []
    for t in teams:
        inv = get_inventory(t["id"])
        monitor.append({
            "Team": t["team_name"],
            "Specialisation": by_id[t["specialization_asset_id"]]["name"],
            "Members": ", ".join(m["full_name"] for m in get_members(t["id"])),
            "Cash": t["cash"],
            "Asset units": sum(x["quantity"] for x in inv),
        })
    st.dataframe(pd.DataFrame(monitor), use_container_width=True, hide_index=True)

    st.markdown("### Recent Transactions")
    tx = (
        q("nexus_transactions")
        .select("*")
        .eq("game_id", game_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )
    st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)
