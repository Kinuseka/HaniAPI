from .obj_globals import global_storage
from collections import UserDict
from .jsparse import full_parser
from .endpoint import Site
from .videoencoder import HlsObject
from typing import Union
import json

class Video(UserDict):
    def __init__(self,page,original_title=None,*args,**kwargs) -> None:
        self._raw_data: dict = page
        self.o_title = original_title
        super().__init__(page)
        self.callback = None
        
    def hls(self, server_u:str, quality:str="720",file="", callback = None, threaded: bool = False) -> HlsObject:
        """Allows more control on how you process the video"""
        if callback:
            self.callback = callback
        vid: Union[dict, None] = None
        _vid_exist = False
        _vid_exist_count = 0
        for server in self._raw_data.get("servers"):
            if server_u == server.get("name"):
                for n, stream in enumerate(server.get("streams")):
                    if quality == stream.get("height"):
                        vid = stream
                        break
                    elif not _vid_exist:
                        _vid_exist = bool(stream.get('url'))
                    _vid_exist_count = n
                else:
                    if _vid_exist:
                        raise ValueError(f'Cannot find streamable object on quality: {quality}p. There are {_vid_exist_count} available')
                    else:
                        raise ValueError("No streamable object found")
                break
        else:
            raise ValueError("Video not found")
        if vid:
            file_name = vid.get("slug")
            url = vid.get("url")
            meta = {}
            meta["filesize"] = vid.get("filesize_mbs")
            if self.o_title:
                file_name = f"{self.o_title} [{quality}p]"
            return HlsObject(url, meta=meta, file_name=file_name, file_type="mkv", file=file, callback=self._callback_handler, simultaneous=threaded)
        
    def _callback_handler(self, *args, **kwargs):
        if self.callback:
            return self.callback(*args, **kwargs)

    def download(self, server_u:str, quality:str="720", file: str = "", callback = None, threaded: bool = True):
        if callback:
            self.callback = callback
        hlsobj = self.hls(server_u,quality=quality,file=file,callback=self._callback_handler,threaded=threaded)
        hlsobj.start()
        return hlsobj.join()

    def quality(self, server_u:str) -> list:
       server_data = [qual for qual in self._raw_data.get("servers") if qual.get('name') == server_u][0]['streams']
       return [each.get('height') for each in server_data if each.get('url', None)]
            
    def servers(self) -> list:
        return [serv.get("name") for serv in self._raw_data.get("servers")]

    def __str__(self):
        return f"<Video object with servers: {len(self.servers())}>"

class Page(UserDict):
    def __init__(self,data:dict,*args,**kwargs) -> None:
        self._raw_data = data
        r = global_storage.global_request.get(self.link())
        self._processed_data = full_parser(r.content)
        super().__init__(data) 

    def get_title(self) -> str:
        return self._raw_data['name']

    def video(self) -> Video:
        return Video(self._processed_data["state"]["data"]["video"]["videos_manifest"], original_title=self.get_title())

    def link(self):
        return f"{Site.video_page}/{self._raw_data['slug']}"

class Data(UserDict):
    def __init__(self,data:dict,*args,**kwargs) -> None:
        self._raw_data = data
        super().__init__(data) 
    
    def page_list(self) -> list:
        res = []
        for i in range(len(self._raw_data['list'])):
            res.append(self.page(i))
        return res
        
    def page(self,len:int) -> Page:
        return Page(self._raw_data['list'][len])

class SearchResult(UserDict):
    def __init__(self,data:dict,*args,**kwargs) -> None:
        self._raw_data = data
        self.hits = json.loads(data['hits'])
        super().__init__(data) 
    
    def page_list(self) -> list:
        res = []
        for i in range(len(self.hits)):
            res.append(self.page(i))
        return res
        
    def page(self,len:int) -> Page:
        return Page(self.hits[len])