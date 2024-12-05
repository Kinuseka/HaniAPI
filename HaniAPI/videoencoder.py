from .obj_globals import global_storage
from CFSession import cfexception
from Crypto.Cipher import AES
from typing import Callable
from pathlib import Path
import threading
import m3u8
import heapq
import os
import time
import ffmpeg
import shutil
import json
def _callback(data):
    return data
#from https://github.com/globocom/m3u8#using-different-http-clients
class RequestsClient():
    def download(self, uri, timeout=None, headers={}, verify_ssl=True):
        o = global_storage.global_request.get(uri, timeout=timeout, headers=headers)
        return o.text, o.url

class VideoFile:
    def __init__ (self, fileName, ext):
        self.file = fileName +'.'+ ext
        self.rawfile = fileName
        # do more stuff
    def open(self, perms, *a, **k):
        return open(self.file,perms, *a, **k)
    
    def remux(self, delete_original = True):
        """Remux the video, generally recommended to make it playable."""
        try:
            (
                ffmpeg
                .input(self.file)
                .output(self.rawfile + ".mp4", c='copy', movflags='faststart')
                .overwrite_output()
                .run()
            )
        except ffmpeg.Error as e:
            print("Something went wrong when remuxing the video")
            print(e)
        finally:
            if delete_original:
                os.remove(self.file)

class HlsObject(threading.Thread):
    """
    An HlsObject is responsible for managing the m3u8 file and downloading the video file. To initiate the download process, use the .start() method.
    """
    def __init__(self,playlist: str, meta:dict, file_name: str, file_type: str, file: str = "", callback: Callable = None, simultaneous = False,*args,**kwargs):
        threading.Thread.__init__(self,*args, *kwargs)
        self.playlist = m3u8.load(playlist, http_client=RequestsClient())
        self.uri = playlist
        self.meta = meta
        self.filename = file_name
        self.filetype = file_type
        self._concurrent = simultaneous
        self.fileloc = file
        self._callback = callback
        self.daemon = False
        self._return = None
        Path(self.fileloc).mkdir(parents=True, exist_ok=True)

        #Threaded variables
        self._t_started = False
        self._t_progress = 0
        self._t_max_all = 0
        self._t_each = {}

    def duration(self):
        return self.playlist.target_duration

    def segments(self):
        return self.playlist.segments

    def decrypt(self,data):
        return
    
    def download(self, suppress_warning = False): #automatic thread handle
        """Use HlsObject.start() if you want to download the video, this is a lowlevel method and should not be invoked"""
        def warn_print(msg):
            if not suppress_warning:
                print(msg)
        def unpad(data):
            # The padding byte is the last byte
            padding_byte = data[-1]
            # Check that all padding bytes are the same
            if all(x == padding_byte for x in data[-padding_byte:]):
                return data[:-padding_byte]
            else:
                raise ValueError("Invalid padding")
        file = os.path.join(self.fileloc,f"{self.filename}.{self.filetype}")
        for key in self.playlist.keys:
            if key:
                new_key = global_storage.global_request.get(key.uri).content
                cipher = AES.new(new_key, AES.MODE_CBC, os.urandom(16))
        if os.path.exists(file): os.remove(file)
        with open(file,"ab") as f:
            if not self._concurrent:
                    for i, segment in enumerate(self.playlist.segments.uri):
                        _col_data = self._dl_proc(segment, callback=self._callback)
                        try:
                            data = cipher.decrypt(_col_data)
                        except ValueError:
                            size = len(_col_data) / 1024
                            if size <= 1:
                                warn_print("[WARN] Segment is less than 1kb, this will be ignored")
                                self._callback({"status": 'post_fetch', 'status_msg': f'segments {i+1}/{len(self.playlist.segments.uri)}','progress': i+1, 'max_segments': len(self.playlist.segments.uri)})
                                return
                            else:
                                warn_print("[WARN] Segment cannot be decoded due to invalid padding, this may cause stuttering on playback")
                                self._callback({"status": 'post_fetch', 'status_msg': f'segments {i+1}/{len(self.playlist.segments.uri)}','progress': i+1, 'max_segments': len(self.playlist.segments.uri)})
                                return
                        f.write(data)
                        self._callback({"status": 'post_fetch', 'status_msg': f'segments {i+1}/{len(self.playlist.segments.uri)}','progress': i+1, 'max_segments': len(self.playlist.segments.uri)})
            else:
                self._child_processes = []
                threading.Thread(target=self._callback_thr, args=(self._callback,),daemon=True).start()
                for index, segment in enumerate(self.playlist.segments.uri):
                    while threading.active_count() >= 10: time.sleep(0.5) #halt thread creation temporarily
                    _daemon_t = Downloader_child(segment, index, self.filename, cipher = cipher, daemon = True)
                    self._child_processes.append(_daemon_t)
                    _daemon_t.status_endpoint(self)
                    _daemon_t.start()
                #wait for threads to finish(unless running as parent thread)
                for each in self._child_processes: each.join()
                time.sleep(0.5) #Sleep for awhile to give threads time to die
                #then sort each file into one
                for seg, each in enumerate(self._child_processes):
                    with open(each.fname, "rb") as chf:
                        data = chf.read()
                        size = len(data) / 1024
                        if size <= 1:
                            if each.error_msg:
                                warn_print(each.error_msg)
                            else:
                                warn_print(f"[WARN] {seg} Segment is less than 1kb, this will be ignored")  
                        f.write(data)
                        f.flush()
                    os.remove(each.fname)
    
    def _callback_thr(self, callback):
        while (not self._isdone_thr(self._child_processes)):
            data = {"status": "threaded", "progress": self._t_progress, "max": self._t_max_all, "final": self.meta.get("filesize"), "done": self._isdone_thr(info_fetch="manyStop"), "finished": self._isdone_thr(info_fetch="manyDone"), "started": len(self._child_processes), "max_segments": len(self.playlist.segments.uri)}
            state = callback(data)
            if state == "StopCallback":
                break

    def _isdone_thr(self, info_fetch = "isDone"):
        child_proc = self._child_processes
        if info_fetch == "isDone":
            return any(child.is_alive() for child in child_proc)
        elif info_fetch == "manyStop":
            return sum(1 if not child.is_alive() else 0 for child in child_proc)
        elif info_fetch == "manyDone":
            return sum(1 if child.done else 0 for child in child_proc) 

    def _dl_proc(self, uri, callback=_callback):
        if not self._concurrent:
            callback({'status':'pre_fetch', 'status_msg': f"Downloading: {uri}", 'progress': uri})
        session = global_storage.global_request
        for i in range(5): #retry 5 times
            try:
                if self._concurrent:
                    self._t_each[uri] = {'done': False}
                r = session.get(uri, stream=True)
                self._max_chunk = r.headers.get('Content-Length')
                self._init_chunk = 0
                _data_chunk = b''
                for chunks in r.iter_content(chunk_size=4096):
                    _init_chunk += len(chunks)
                    _data_chunk += chunks
                    if not self._concurrent:
                        callback({'status':'stream','status_msg': f"Bytes: {self._init_chunk}/{self._max_chunk}",'progress': self._init_chunk, 'max_bytes': self._max_chunk,'uri': f'{uri}'})
                else:
                    return _data_chunk
            except cfexception.NetworkError:
                continue
        else:
            raise cfexception.Timeout("reached maximum limit")
        
    def cache_clear(self):
        cache_dir = os.path.join(os.getcwd(),".cache")
        if not os.path.exists(cache_dir): return
        for filename in os.listdir(cache_dir):
            # Create absolute path
            filepath = os.path.join(cache_dir, filename)
            try:
                # If it is a file or symlink, remove it
                if os.path.isfile(filepath) or os.path.islink(filepath):
                    os.unlink(filepath)
                # If it is a directory, remove it
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
            except Exception as e:
                print('[CacheClean] Failed to delete %s. Reason: %s' % (filepath, e))


    def get_m3u8(self):
        """Dumps the m3u8 file into the file directory"""
        self._return = self.playlist.dump(os.path.join(self.fileloc, f"{self.filename}.m3u8"))

    def join(self) -> VideoFile:
        threading.Thread.join(self)
        return VideoFile(os.path.join(f"{self.fileloc}",f"{self.filename}"),self.filetype)

    def run(self):
        """Start the download"""
        return self.download()
    

class Downloader_child(threading.Thread):
    def __init__(self, uri, index, filename, cipher, *args, **kwargs):
        threading.Thread.__init__(self,*args, **kwargs)
        self.uri = uri
        self.done = False
        self.error = False
        self.retry = 0   
        self.original_f = filename
        self.index = index
        self.fname = os.path.join(os.getcwd(),".cache",f"{filename}_{index}.part")
        self.progress = 0
        self.max = 0
        self.key = cipher
        self.error_msg = None
        self._data_return = None
        self._endpoint = None
        Path(os.path.join(os.getcwd(),".cache")).mkdir(parents=True, exist_ok=True)

    def status_endpoint(self, obj):
        """
        obj should contain variables:
        obj._t_started: bool
        obj._t_progress: int
        obj._t_max_all: int
        obj._t_each: dict
        """
        self._endpoint = obj

    def reset_var(self):
        self.progress = 0
        self.max = 0

    def download(self):
        session = global_storage.global_request
        for i in range(30): #retry 30 times
            with open(self.fname, "wb") as f:
                try:
                    r = session.get(self.uri, stream=True,timeout=120)
                    self.max = r.headers.get('Content-Length')
                    # self._endpoint._t_max_all += self.max if isinstance(self.max, (int, float)) else 0
                    self._init_chunk = 0
                    _data_chunk = b''
                    for chunks in r.iter_content(chunk_size=4096):
                        self.progress += len(chunks)
                        self._endpoint._t_progress += len(chunks)
                        _data_chunk += chunks
                    else:                
                        _decrypted_chunk = self._decrypt(_data_chunk)
                        self._endpoint._t_max_all += len(_decrypted_chunk)
                        f.write(_decrypted_chunk)
                        f.flush()
                        self.done = True
                        return #Most important part
                except cfexception.CFException:
                    self._endpoint._t_max_all -= self.max if isinstance(self.max, int and float) else 0
                    self._endpoint._t_progress -= self.progress
                    self.retry += 1
                    self.reset_var()
                    continue
        else:
            self.error = True
            raise cfexception.Timeout("reached maximum limit")

    def _decrypt(self, data):
        try:
            return self.key.decrypt(data)
        except ValueError:
            self.error_msg = f"[WARN] {self.index} Segment cannot be decoded due to invalid padding, this may cause stuttering/skipping on playback"
            self.error = True
            return b''
        
    def join(self):
        threading.Thread.join(self)

    def run(self):
        #print(self.getName()+ " Has been opened")
        self.download()
        