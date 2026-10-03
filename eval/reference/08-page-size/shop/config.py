import os

DEFAULTS = {
    "page_size": 25,
    "currency": "USD",
    "db_path": ":memory:",
}


def load_config(env=None):
    env = os.environ if env is None else env
    cfg = dict(DEFAULTS)
    if "SHOP_PAGE_SIZE" in env:
        cfg["page_size"] = int(env["SHOP_PAGE_SIZE"])
    if "SHOP_DB_PATH" in env:
        cfg["db_path"] = env["SHOP_DB_PATH"]
    return cfg
