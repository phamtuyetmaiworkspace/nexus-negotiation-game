
import streamlit as st
from supabase import create_client, Client
import pandas as pd

st.set_page_config(page_title="NEXUS Negotiation Game", page_icon="🧩", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
ADMIN_PIN = str(st.secrets.get("ADMIN_PIN", ""))

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def q(table):
    return sb.table(table)

def rpc(name, params):
    return sb.rpc(name, params).execute().data

@st.cache_data(ttl=20)
def get_games():
    return q("nexus_games").select("id,name,class_label,current_period,market_open").order("created_at", desc=True).execute().data

@st.cache_data(ttl=20)
def get_assets():
    rows = q("nexus_assets").select("id,code,name,category,emoji").eq("active", True).execute().data
    by_id = {r["id"]: r for r in rows}
    by_code = {r["code"]: r for r in rows}
    return rows, by_id, by_code

def get_game(game_id):
    return q("nexus_games").select("*").eq("id", game_id).single().execute().data

def get_team(team_id):
    return q("nexus_teams").select("*").eq("id", team_id).single().execute().data

def get_team_no(game_id, team_no):
    data = q("nexus_teams").select("*").eq("game_id", game_id).eq("team_no", team_no).execute().data
    return data[0] if data else None

def get_members(team_id):
    return q("nexus_members").select("full_name,display_order").eq("team_id", team_id).order("display_order").execute().data

def get_inventory(team_id):
    assets, by_id, _ = get_assets()
    rows = q("nexus_inventory").select("asset_id,quantity").eq("team_id", team_id).gt("quantity", 0).execute().data
    out = []
    for r in rows:
        a = by_id.get(r["asset_id"], {})
        out.append({
            "asset_id": r["asset_id"],
            "code": a.get("code"),
            "asset": f'{a.get("emoji","")} {a.get("name","")}'.strip(),
            "category": a.get("category"),
            "quantity": r["quantity"],
        })
    return out

def get_directory(game_id):
    teams = q("nexus_teams").select("id,team_no,team_name,specialization_asset_id").eq("game_id", game_id).order("team_no").execute().data
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
    assets, by_id, _ = get_assets()
    rows = q("nexus_market_prices").select("asset_id,buy_price").eq("game_id", game_id).eq("period", period).execute().data
    out = []
    for r in rows:
        a = by_id.get(r["asset_id"], {})
        out.append({
            "Asset": f'{a.get("emoji","")} {a.get("name","")}'.strip(),
            "Category": a.get("category",""),
            "International Market": r["buy_price"],
        })
    return sorted(out, key=lambda x: (x["Category"], x["Asset"]))

def verify_team(game_id, team_no, pin):
    data = rpc("nexus_verify_team_pin", {
        "p_game_id": game_id,
        "p_team_no": int(team_no),
        "p_pin": str(pin)
    })
    return data

def team_name(team_id):
    t = get_team(team_id)
    return t["team_name"]

def get_pending_for_team(team_id):
    rows = (
        q("nexus_transactions")
        .select("*")
        .eq("counterparty_team_id", team_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return rows

def describe_transaction(tx):
    _, by_id, _ = get_assets()
    lines = q("nexus_transaction_lines").select("*").eq("transaction_id", tx["id"]).execute().data
    give = []
    receive = []
    for line in lines:
        if line["asset_id"]:
            a = by_id.get(line["asset_id"], {})
            text = f'{line["quantity"]} × {a.get("emoji","")} {a.get("name","")}'.strip()
        else:
            text = f'{line["credits"]} Credits'
        if line["from_team_id"] == tx["proposer_team_id"]:
            give.append(text)
        else:
            receive.append(text)
    return " + ".join(give), " + ".join(receive)

def current_game_selector(label="Game session"):
    games = get_games()
    if not games:
        st.error("No game session exists.")
        st.stop()
    opts = {f'{g["name"]} ({g.get("class_label") or "no class label"})': g["id"] for g in games}
    chosen = st.selectbox(label, list(opts.keys()))
    return opts[chosen]

# ---------- Public header ----------
st.title("🧩 NEXUS — Four Eras Negotiation Game")

mode = st.sidebar.radio("Mode", ["Public Market & Directory", "Team Trader", "Teacher"])

if mode == "Public Market & Directory":
    game_id = current_game_selector()
    game = get_game(game_id)
    st.subheader(f'{game["name"]} — Period {game["current_period"]}')
    st.caption("Market status: " + ("🟢 OPEN" if game["market_open"] else "🔴 CLOSED"))

    tab1, tab2 = st.tabs(["International Market", "Team Directory"])
    with tab1:
        st.dataframe(pd.DataFrame(get_market_prices(game_id, game["current_period"])), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(pd.DataFrame(get_directory(game_id)), use_container_width=True, hide_index=True)

elif mode == "Team Trader":
    if "team_id" not in st.session_state:
        game_id = current_game_selector()
        team_no = st.number_input("Team number", min_value=1, step=1)
        pin = st.text_input("Trader PIN", type="password")
        if st.button("Enter Team Control", type="primary"):
            tid = verify_team(game_id, team_no, pin)
            if tid:
                st.session_state["team_id"] = tid
                st.session_state["game_id"] = game_id
                st.rerun()
            else:
                st.error("Invalid Team number or Trader PIN.")
        st.stop()

    team_id = st.session_state["team_id"]
    game_id = st.session_state["game_id"]
    team = get_team(team_id)
    game = get_game(game_id)
    assets, by_id, by_code = get_assets()

    top1, top2, top3 = st.columns([2,1,1])
    with top1:
        st.subheader(team["team_name"])
    with top2:
        st.metric("Cash", team["cash"])
    with top3:
        st.metric("Period", game["current_period"])

    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

    tabs = st.tabs(["My Team", "Trade", "Build", "International Market", "History"])

    with tabs[0]:
        members = get_members(team_id)
        st.write("**Members:** " + ", ".join(m["full_name"] for m in members))
        inv = pd.DataFrame(get_inventory(team_id))
        if inv.empty:
            st.info("No assets currently held.")
        else:
            st.dataframe(inv[["asset","category","quantity"]], use_container_width=True, hide_index=True)

        st.markdown("### Pending offers")
        pending = get_pending_for_team(team_id)
        if not pending:
            st.caption("No pending offers.")
        for tx in pending:
            proposer = team_name(tx["proposer_team_id"])
            proposer_gives, counter_gives = describe_transaction(tx)
            with st.container(border=True):
                st.write(f"**From {proposer}**")
                st.write(f"They give: **{proposer_gives}**")
                st.write(f"You give: **{counter_gives}**")
                c1, c2 = st.columns(2)
                if c1.button("Accept", key=f'acc_{tx["id"]}', type="primary", disabled=not game["market_open"]):
                    try:
                        rpc("nexus_accept_trade", {
                            "p_transaction_id": tx["id"],
                            "p_accepting_team_id": team_id
                        })
                        st.success("Trade completed.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                if c2.button("Reject", key=f'rej_{tx["id"]}'):
                    try:
                        rpc("nexus_reject_trade", {
                            "p_transaction_id": tx["id"],
                            "p_rejecting_team_id": team_id
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with tabs[1]:
        st.markdown("### Create trade offer")
        directory = q("nexus_teams").select("id,team_no,team_name").eq("game_id", game_id).neq("id", team_id).order("team_no").execute().data
        team_opts = {t["team_name"]: t["id"] for t in directory}
        target_name = st.selectbox("Counterparty", list(team_opts.keys()))
        target_id = team_opts[target_name]

        st.caption("MVP v0.1: each side can offer either one asset line or Credits. Package deals will be added next.")
        my_type = st.radio("I give", ["Asset", "Credits"], horizontal=True, key="mygive")
        if my_type == "Asset":
            inv = [x for x in get_inventory(team_id) if x["quantity"] > 0]
            my_asset_opts = {f'{x["asset"]} (you have {x["quantity"]})': x["code"] for x in inv}
            if not my_asset_opts:
                st.warning("You have no assets to offer.")
                my_payload = None
            else:
                label = st.selectbox("My asset", list(my_asset_opts.keys()))
                qty = st.number_input("Quantity", min_value=1, step=1)
                my_payload = [{"asset_code": my_asset_opts[label], "quantity": int(qty)}]
        else:
            credits = st.number_input("Credits I give", min_value=1, step=1)
            my_payload = [{"credits": int(credits)}]

        their_type = st.radio("I request", ["Asset", "Credits"], horizontal=True, key="theirgive")
        if their_type == "Asset":
            token_assets = [a for a in assets if a["category"] in ("resource","skill","item")]
            asset_opts = {f'{a["emoji"] or ""} {a["name"]}'.strip(): a["code"] for a in token_assets}
            label2 = st.selectbox("Requested asset", list(asset_opts.keys()))
            qty2 = st.number_input("Requested quantity", min_value=1, step=1)
            their_payload = [{"asset_code": asset_opts[label2], "quantity": int(qty2)}]
        else:
            credits2 = st.number_input("Credits requested", min_value=1, step=1)
            their_payload = [{"credits": int(credits2)}]

        if st.button("Send offer", type="primary", disabled=not game["market_open"] or my_payload is None):
            try:
                txid = rpc("nexus_create_trade", {
                    "p_game_id": game_id,
                    "p_proposer_team_id": team_id,
                    "p_counterparty_team_id": target_id,
                    "p_period": int(game["current_period"]),
                    "p_proposer_gives": my_payload,
                    "p_counterparty_gives": their_payload,
                    "p_note": None
                })
                st.success(f"Offer sent. Transaction ID: {txid}")
            except Exception as e:
                st.error(str(e))

    with tabs[2]:
        st.markdown("### Build Item")
        recipe_rows = q("nexus_recipes").select("*").execute().data
        opts = {}
        for r in recipe_rows:
            o = by_id[r["output_asset_id"]]
            res = by_id[r["resource_asset_id"]]
            sk = by_id[r["skill_asset_id"]]
            label = f'{o["emoji"] or ""} {o["name"]} = {res["name"]} + {sk["name"]}'
            opts[label] = o["code"]
        build_choice = st.selectbox("Recipe", list(opts.keys()))
        build_qty = st.number_input("Build quantity", min_value=1, step=1, key="build_qty")
        if st.button("Build", type="primary", disabled=not game["market_open"]):
            try:
                result = rpc("nexus_build_item", {
                    "p_game_id": game_id,
                    "p_team_id": team_id,
                    "p_output_asset_code": opts[build_choice],
                    "p_quantity": int(build_qty)
                })
                st.success(str(result))
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with tabs[3]:
        st.markdown("### Sell to International Market")
        prices = get_market_prices(game_id, game["current_period"])
        inv = get_inventory(team_id)
        price_map = {}
        raw_prices = q("nexus_market_prices").select("asset_id,buy_price").eq("game_id", game_id).eq("period", game["current_period"]).execute().data
        raw_map = {r["asset_id"]: r["buy_price"] for r in raw_prices}
        for x in inv:
            if x["asset_id"] in raw_map:
                price_map[f'{x["asset"]} — {raw_map[x["asset_id"]]} each (you have {x["quantity"]})'] = (x["code"], raw_map[x["asset_id"]])
        if not price_map:
            st.info("No sellable assets.")
        else:
            sell_label = st.selectbox("Asset", list(price_map.keys()))
            sell_code, unit_price = price_map[sell_label]
            sell_qty = st.number_input("Quantity to sell", min_value=1, step=1, key="sell_qty")
            st.write(f"International Market pays **{unit_price * int(sell_qty)} Credits**.")
            if st.button("Sell to Market", type="primary", disabled=not game["market_open"]):
                try:
                    result = rpc("nexus_sell_to_market", {
                        "p_game_id": game_id,
                        "p_team_id": team_id,
                        "p_asset_code": sell_code,
                        "p_quantity": int(sell_qty)
                    })
                    st.success(str(result))
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with tabs[4]:
        tx = (
            q("nexus_transactions")
            .select("id,period,transaction_type,proposer_team_id,counterparty_team_id,status,created_at,completed_at,note")
            .eq("game_id", game_id)
            .or_(f"proposer_team_id.eq.{team_id},counterparty_team_id.eq.{team_id}")
            .order("created_at", desc=True)
            .execute()
            .data
        )
        st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)

else:
    game_id = current_game_selector()
    admin_pin = st.text_input("Teacher PIN", type="password")
    if admin_pin != ADMIN_PIN:
        st.info("Enter the Teacher PIN.")
        st.stop()

    game = get_game(game_id)
    st.subheader(f'Teacher Dashboard — {game["name"]}')
    c1, c2, c3 = st.columns(3)
    c1.metric("Period", game["current_period"])
    c2.metric("Market", "OPEN" if game["market_open"] else "CLOSED")
    team_count = q("nexus_teams").select("id", count="exact").eq("game_id", game_id).execute().count
    c3.metric("Teams", team_count)

    a,b,c = st.columns(3)
    if a.button("Open Market", disabled=game["market_open"]):
        rpc("nexus_set_market_open", {"p_game_id": game_id, "p_open": True})
        st.cache_data.clear()
        st.rerun()
    if b.button("Close Market", disabled=not game["market_open"]):
        rpc("nexus_set_market_open", {"p_game_id": game_id, "p_open": False})
        st.cache_data.clear()
        st.rerun()
    if c.button("Advance Period", disabled=game["current_period"] >= 4):
        try:
            rpc("nexus_advance_period", {"p_game_id": game_id})
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.markdown("### Team monitor")
    teams = q("nexus_teams").select("id,team_no,team_name,cash,specialization_asset_id").eq("game_id", game_id).order("team_no").execute().data
    _, by_id, _ = get_assets()
    monitor = []
    for t in teams:
        inv = get_inventory(t["id"])
        total_units = sum(x["quantity"] for x in inv)
        monitor.append({
            "Team": t["team_name"],
            "Specialisation": by_id[t["specialization_asset_id"]]["name"],
            "Cash": t["cash"],
            "Asset units held": total_units
        })
    st.dataframe(pd.DataFrame(monitor), use_container_width=True, hide_index=True)

    st.markdown("### Recent transactions")
    tx = q("nexus_transactions").select("*").eq("game_id", game_id).order("created_at", desc=True).limit(50).execute().data
    st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)
