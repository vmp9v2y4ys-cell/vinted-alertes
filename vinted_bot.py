"""
Bot de veille Vinted : surveille de nouvelles annonces et envoie une alerte Discord.

Installation :  pip install requests
Lancement    :  python vinted_bot.py
"""
import time
import random
import requests

# ================== CONFIG ==================
DOMAIN = "https://www.vinted.fr"
DISCORD_WEBHOOK = "COLLE_ICI_TON_WEBHOOK_DISCORD"

# Une entrée = une recherche surveillée
SEARCHES = [
    {
        "name": "Nike Air Max",
        "search_text": "nike air max",
        "price_to": 40,          # prix max en €
        "price_from": 5,         # évite les annonces à 1 € bidons
        "must_not_contain": ["fake", "réplique", "replica", "lot de"],
    },
    # {"name": "Levi's 501", "search_text": "levis 501", "price_to": 20},
]

CHECK_EVERY = (45, 90)   # intervalle aléatoire en secondes (ne pas descendre trop bas)
PER_PAGE = 20
# ============================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)
seen_ids = set()


def refresh_session():
    """Récupère les cookies de session nécessaires à l'API."""
    session.cookies.clear()
    session.get(DOMAIN, timeout=15)


def fetch_items(search):
    params = {
        "search_text": search["search_text"],
        "order": "newest_first",
        "per_page": PER_PAGE,
    }
    if "price_to" in search:
        params["price_to"] = search["price_to"]
    if "price_from" in search:
        params["price_from"] = search["price_from"]

    r = session.get(f"{DOMAIN}/api/v2/catalog/items", params=params, timeout=15)
    if r.status_code in (401, 403):
        refresh_session()
        r = session.get(f"{DOMAIN}/api/v2/catalog/items", params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("items", [])


def get_price(item):
    p = item.get("price")
    if isinstance(p, dict):
        return float(p.get("amount", 0))
    return float(p or 0)


def is_interesting(item, search):
    title = (item.get("title") or "").lower()
    return not any(w.lower() in title for w in search.get("must_not_contain", []))


def notify(item, search):
    photo = (item.get("photo") or {}).get("url")
    embed = {
        "title": item.get("title", "Annonce"),
        "url": item.get("url") or f"{DOMAIN}/items/{item['id']}",
        "description": (
            f"💶 **{get_price(item):.2f} €**\n"
            f"🏷️ {item.get('brand_title') or '-'}  |  📏 {item.get('size_title') or '-'}\n"
            f"✨ {item.get('status') or '-'}"
        ),
        "footer": {"text": f"Recherche : {search['name']}"},
    }
    if photo:
        embed["thumbnail"] = {"url": photo}
    requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]}, timeout=15)


def run():
    refresh_session()

    # Premier passage : on mémorise l'existant sans alerter
    for s in SEARCHES:
        try:
            for it in fetch_items(s):
                seen_ids.add(it["id"])
        except Exception as e:
            print(f"[init] {s['name']} : {e}")
    print("Bot lancé, surveillance en cours...")

    while True:
        for s in SEARCHES:
            try:
                for it in fetch_items(s):
                    if it["id"] in seen_ids:
                        continue
                    seen_ids.add(it["id"])
                    if is_interesting(it, s):
                        notify(it, s)
                        print(f"[+] {it.get('title')} - {get_price(it)} €")
            except Exception as e:
                print(f"[erreur] {s['name']} : {e}")
            time.sleep(random.uniform(3, 8))
        time.sleep(random.uniform(*CHECK_EVERY))


if __name__ == "__main__":pp
    run()
