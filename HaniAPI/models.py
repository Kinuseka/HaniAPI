from datetime import datetime
from .obj_globals import global_storage
from .endpoint import Site
from .prettier import Prettify
from .objectmodel import Data, Page
try:
    from functools import cache
except ImportError:
    from functools import lru_cache as cache
from hashlib import sha256
from typing import Generator
from collections import UserDict
import time


class User:
    def __init__(self,data: dict) -> None:
        self._raw_whole = data
        self.raw = data.get("user")
        self.env = data.get("env")
        if self.raw:
            self.email = self.raw.get('email')
            self.username = self.raw.get('name')
            self.user_id = self.raw.get('number')
            self.coins = self.raw.get('coins')
        else:
            self.email = self.username = self.user_id = self.coins = None

    def get_all(self):
        return self.raw

    def _isoformat(self, datetime_str) -> datetime:
        try:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            # Perhaps the datetime has a whole number of seconds with no decimal
            # point. In that case, this will work:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
 
    def prettify(self):
        """prints all the necessary user data"""
        pret = Prettify()
        if self.raw:
            pret.add_tab('Account Details')
            pret.add_sort('Username', f"{self.raw.get('name')}#{self.raw.get('number')}")
            pret.add_sort("Email", f"{self.raw.get('email')}")
            pret.add_sort("Times signed in", f"{self.raw.get('sign_in_count')}")
            if self.raw.get('is_able_to_access_premium'):
                pret.add_tab("Membership")
                pret.add_sort('Premium',f"{self.raw.get('is_able_to_access_premium')}")
                time_start = self._isoformat(self.raw.get('alt_subscription_period_start')).strftime('%A %d, %B %Y (%H:%M:%S)')
                time_end = self._isoformat(self.raw.get('alt_subscription_period_end')).strftime(f'%A %d, %B %Y (%H:%M:%S)')
                pret.add_sort('Subscription Started',f"{time_start}")
                pret.add_sort('Subscription End    ',f"{time_end}")
            pret.add_tab("")
        else:
            pret.add_tab('Account Details')
            pret.add_line('You are not logged in')
            pret.add_tab("")
        return pret.prettystring()
    
    def _sha256_hash(self, plain):
        """Get SHA256 hash."""
        hash = sha256()
        hash.update(plain.encode())
        return hash.hexdigest()

    def _mobile_ver(self, mobile):
        if "_build_number" in mobile.keys():
            version = mobile["_build_number"]
        elif "osts_build_number" in mobile.keys():
            version = mobile["osts_build_number"]
        elif "severilous_build_number" in mobile.keys():
            version = mobile["severilous_build_number"]
        return version

    def coin_cooldown(self) -> dict:
        """Calculates how long until you are able to collect coins again"""
        previous_time = self._isoformat(self.raw.get("last_rewarded_ad_clicked_at")).timestamp() if self.raw.get("last_rewarded_ad_clicked_at") else 0
        time_elapsed = time.time() - previous_time
        time_remaining = 3 * 3600 - time_elapsed
        #disrespect API
        if time_elapsed < 3 * 3600:
            return {"is_avail": False, "endsOn": time_remaining}
        else:
            return {"is_avail": True, "endsOn": time_remaining}

    def get_coins(self) -> dict: #Reversed engineered by: https://github.com/WeaveAche
        """Collects coins from the site"""
        status = self.coin_cooldown()
        if status['is_avail']:
            #generate hash
            version = self._mobile_ver(self.env['mobile_apps'])
            uid = self.raw['id']
            curr_time = str(int(time.time()))
            to_hash = f"coins{version}|{uid}|{curr_time}|coins{version}"
            #generate header
            headers = global_storage.global_login_headers()
            XClaim = str(int(time.time()))
            headers['X-Claim'] = XClaim
            headers["X-Signature"] = self._sha256_hash(f"9944822{XClaim}8{XClaim}113")
            headers["X-Session-Token"] = self._raw_whole["session_token"]
            headers.pop("Content-Type")
            data = global_storage.global_coin_data()
            data["reward_token"] = self._sha256_hash(to_hash) + f"|{curr_time}"
            data["version"] = f"{version}"
            s = global_storage.global_request
            s.session.headers.update(headers)
            resp = s.post(Site.api_coins, data=data)
            resp_json = resp.json()
            if resp_json.get("errors", None):
                return {"status": False, "reason": resp_json['errors'], "endsOn": status['endsOn']}
            return {"status": True, "endsOn": status['endsOn'], "reward": resp_json.get('rewarded_amount', 0)}
        else:
            return {"status": False, "reason": "Coins under cooldown", "endsOn": status['endsOn']}

    def __str__(self) -> str:
        return self.prettify()

class Search(UserDict):
    def __init__(self, data: dict) -> None:
        self.raw = data
        self.hits = self.raw.get("hits") #list of dict

    def prettify(self) -> None:
        pret = Prettify()
        title_lists = lambda: self.result_title(self.hits)
        longest = len(max(title_lists(),key=len))
        pret.add_tab('Results',lines=longest)
        for title in title_lists():
            pret.add_line(title)
        else:
            pret.add_tab('',lines=longest)
        return pret.prettystring()
    
    def result_title(self, data) -> Generator[dict, dict, dict]:
        for each in data:
            yield each["name"]
    
    def result_get(self, num:int):
        return Data(self.hits[num])

    def __str__(self) -> str:
        return self.prettify()

    def __repr__(self) -> str:
        return f'<Search Obj, {len(self.video_datas)} at self.video_datas, {len(self.sections)} at self.sections>'

    #@cache()
    def _col_data(self, target_name:str=None):
        target_name = target_name
        self._recent_up = []
        ids = []
        collected = []
        for obj in self.sections:
            if obj.get("title") == target_name:
                ids = obj.get("hentai_video_ids")
                break
        else:
            return None
        for vobj in self.video_datas:
            if vobj.get("id") in ids:
                collected.append(vobj)
        else:
            return {'list':collected}
        
class Homepage:
    def __init__(self, data: dict) -> None:
        self.raw = data
        self.sections = self.raw.get("sections") #list of dict
        self.video_datas = self.raw.get("hentai_videos") #list

    def prettify(self) -> None:
        pret = Prettify()
        title_lists = lambda: self.result_title(self.recent_uploads()['list'])
        longest = len(max(title_lists(),key=len))
        pret.add_tab('Recently Uploaded',lines=longest)
        for title in title_lists():
            pret.add_line(title)
        else:
            pret.add_tab('',lines=longest)
        return pret.prettystring()
    
    def result_title(self, data) -> Generator[dict, dict, dict]:
        for each in data:
            yield each["name"]

    def __str__(self) -> str:
        return self.prettify()

    def __repr__(self) -> str:
        return f'<Homepage Obj, {len(self.video_datas)} at self.video_datas, {len(self.sections)} at self.sections>'

    #@cache()
    def _col_data(self, target_name:str=None):
        target_name = target_name
        self._recent_up = []
        ids = []
        collected = []
        for obj in self.sections:
            if obj.get("title") == target_name:
                ids = obj.get("hentai_video_ids")
                break
        else:
            return None
        for vobj in self.video_datas:
            if vobj.get("id") in ids:
                collected.append(vobj)
        else:
            return {'list':collected}
        
    #Data

    def recent_uploads(self) -> Data:
        return Data(self._col_data("Recent Uploads"))
            
    def new_releases(self) -> Data:
        return Data(self._col_data("New Releases"))

    def trending(self) -> Data:
        return Data(self._col_data("Trending"))
    
    def random(self) -> Data:
        return Data(self._col_data("Random"))

    def recent_likes(self) -> Data:
        return Data(self._col_data("My Recent 10 Likes"))




