#Stores Important global vars

class global_storage:
    global_request = None
    global_headed_cookie = "hanime.cookie"
    global_cookie = lambda: {"domain": ".hanime.tv", "name": "htv3session", "path": "/", "secure": False, "value": None }
    global_login_headers= lambda: {"X-Signature-Version": "app2", "X-Claim": None, "X-Signature": None, "Content-Type": "application/json;charset=utf-8"}
    global_coin_data = lambda: {"reward_token": None, "version": None}