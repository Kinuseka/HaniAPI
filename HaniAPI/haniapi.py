from .obj_globals import global_storage
from .models import User, Homepage
from .objectmodel import Video, SearchResult
from .endpoint import Targets, PreData, Site
from .jsparse import parse_js, full_parser
from bs4 import BeautifulSoup
from hashlib import sha256
import CFSession
import json, re
import os, sys
import time

class API:
    "Authenticator for API"
    def __init__(self,username=None,password=None,token=None,process_name=None) -> None:
        global global_request
        self.token = token
        self.user = None
        if process_name:
            global_storage.global_headed_cookie = process_name
        self.session = CFSession.cfSession(directory=Targets.directory)
        global_storage.global_request = self.session
        self.previous_cache = [] #stores result in memory
        self._memory_store_max = 10

    def refresh_cookie(self) -> bool:
        if not self.session.set_cookies():
            cookie = CFSession.cfCookieHandler(global_storage.global_headed_cookie)
            try:
                cookie.load(self.session)
                return True
            except FileNotFoundError:
                return False
        else:
            return True

    def login(self, username = None, password = None, cache: bool = True, headless = True) -> User:
        """Logs you in into the website. returns user object if successful"""
        #User interfaced Login Requires to solve captcha
        def login_web():
            session = CFSession.cfSimulacrum(directory=Targets.directory)
            session.copen(Site.auth, process_timeout=200)
            session.find()
            session.search(target_title=["Sign In - hanime.tv"])
            self.refresh_cookie() #Set cookie into session
        #Headless login
        def login_direct(): #Reversed engineered by: https://github.com/WeaveAche
            XClaim = str(int(time.time()))
            hash = sha256()
            hash.update(f"9944822{XClaim}8{XClaim}113".encode()) 
            XSig = hash.hexdigest()
            self.session.session.headers.update()
            headers = global_storage.global_login_headers()
            headers['X-Claim'] = XClaim
            headers['X-Signature'] = XSig
            resp = self.session.post(
                Site.api_auth,
                headers=headers, 
                data=f'{{"burger":"{username}","fries":"{password}"}}'
            )
            api_response = resp.json()
            #Important values
            session_token = api_response["session_token"]
            #Build the cookie
            cookie = global_storage.global_cookie()
            cookie['value'] = session_token
            self.session.session.cookies.set(**cookie)
            if cache:
                cookie = CFSession.cfCookieHandler(global_storage.global_headed_cookie)
                cookie.dump(self.session)
            self.refresh_cookie()

        if not os.path.exists(Targets.directory.cache_path()): os.makedirs(Targets.directory.cache_path(), exist_ok=True)
        if os.path.exists(Targets.directory.cookie_path()) and cache:
            account_state = self.account_details()
            if account_state.raw:
                return account_state
        elif os.path.exists(os.path.join(Targets.directory.cache_path(),global_storage.global_headed_cookie)) and cache:
            self.refresh_cookie()
            account_state = self.account_details()
            if account_state.raw:
                return account_state
        if (headless):
            if not (username and password):
                raise ValueError("Username and password is empty while headless mode is True.")
            login_direct()
        elif (not headless):
            login_web()
        self.user = self.account_details()
        return self.user

    def account_details(self) -> User:
        r = self.session.get(Site.account)
        soup = self._parse_site(r.content)
        return User(self._scr_api(soup.find_all("script"))["state"])
        
    def logout(self):
        if os.path.exists(Targets.directory.cookie_path()):
            os.remove(Targets.directory.cookie_path())
        elif os.path.exists(os.path.join(Targets.directory.cache_path(), global_storage.global_headed_cookie)):
            os.remove(os.path.join(Targets.directory.cache_path(), global_storage.global_headed_cookie))
        self.session.session.cookies.clear()

    def search(self, search, broad_search = False, tags = [], brands = [], blacklist = []):
        """
        search: Keywords to search for title
        broad_search: look for video that matches to atleast 1 tag, DEFAULT=FALSE
        tags: tags
        brands: brands
        blacklist: blacklist
        """
        search_data = PreData.search_post()
        search_data["search_text"] = search
        search_data["tags"] = tags
        search_data["brands"] = brands
        search_data["blacklist"] = blacklist
        if broad_search:
            search_data["tags_mode"] = "OR"
        else:
            search_data["tags_mode"] = "AND"
        r = self.session.post(Site.search_api,json=search_data)
        return SearchResult(r.json())

    def homepage(self):
        return Homepage(self.data_page()["state"]["data"]["landing"])
    
    def download(self, video: Video):
        r = self.session.get(video.__str__())
        r.raise_for_status()
        soup = self._parse_site(r.content)
        a = self._scr_api(soup.find_all("script"))
        self._de_dump_soup(str(soup))

    def data_page(self):
        r = self.session.get(Site.home)
        r.raise_for_status()
        soup = self._parse_site(r.content)
        return self._scr_api(soup.find_all("script"))
    
    def _scr_api(self, soup): #automatic scraper for the API json. If there are multiple script then bruteforce
        return parse_js(soup)

    def _parse_site(self,site):
        return BeautifulSoup(site, "html.parser")

    def _de_dump_data(self,data,name="dump.json"):
        json.dump(data, open(name,"w"))

    def _de_dump_soup(self,data,name="dump.html"):
        open(name,"w",encoding="utf-8").write(data)
        
    def __getattribute__(self,name):
        attr = object.__getattribute__(self, name)
        if hasattr(attr, '__call__'):
            def memStore(*args, **kwargs):
                data = attr(*args, **kwargs)
                self.previous_cache.append(data)
                if len(self.previous_cache) >= self._memory_store_max: self.previous_cache.pop() #Clear last memory if hit max
                return data
            return memStore
        else:
            return attr