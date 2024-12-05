# HaniAPI
An Hanime API by using webscraping to collect data.

### Disclaimer: Functional but not stable, might some more bug swatting.

# Requirements
### System
* ffmpeg
### Python Libraries
* CFSession>=0.2.0
* beautifulsoup4>=4.10.0
* ffmpeg-python
* git+https://github.com/globocom/m3u8.git
* pycryptodome
* python-dateutil

# How to Utilize

## Simple Usage (login, and search)

### Initialize API
```py
import haniAPI

hani = haniAPI.API()
```

### Login to hanime.tv
```py
user = hani.login(username, password) #Returns haniAPI.models.User
```
### See user details
```py
#See simplified user details
print(user.prettify())

#See raw user details
user.raw # <- this is a dict
```

### Search for titles
```py
SearchResult = hani.search(search="<Enter title Here>") #<- returns SearchResult object, can be treated as dict
page_lists = SearchResult.page_list() #Get a list of all the results.
```

### Get specific result from search
```py
page = SearchResult.page(index) #Get the result according to its index list value, returns a Page object
```

### What can you do with Page object
```py
page.get_title() #Returns the title
page.link() #Returns the link
video = page.video() #Returns a Video object 
```

### Get the video metadata (Servers, and Quality options)
```py
video = page.video()
servers = video.servers() #Returns a list of all possible servers

selected_server = servers[0] #Lets say lets get the first server in the list
possible_qualities = video.quality(selected_server) #Returns a list of all possible quality options according to your selected server
```

### Download the video file
In order to download you will need 2 things, **quality option** and the **server** you selected

**Simple Method:**
```py
VideoFile = video.download(server_u=server, quality=quality) #Starts the download and waits until it is finished, returns a VideoFile object that allows you to manipulate the final output of the video, ill explain later why.
```

**More control method:**

This allows you more control over your process
```py
HlsObject = video.hls(server_u=server, quality=quality) #Returns HlsObject object

HlsObject.start() #Starts the download without blocking the mainthread

... #At this point you can do stuff here while the video is downloading

VideoFile = HlsObject.join() #Waits until the download is finished, returns VideoFile object similar to video.download()
```

## Postprocessing

When you download the video file, it may be unstable to play on some media players. To mitigate this, we need to remux the video and turn it into fully fledged mp4 file.

```py
VideoFile.remux(delete_original=True) #delete_original parameter if true (Default will always be true) deletes the original video after the remux is finished 
```

## How to view the download status. 

Look at this sample code

```py
def getter(data):
    max_segments = 0
    current_segments = 0
    loading = False
    status = data["status"]
    if status == "stream":
        print(f"| Downl: {data['progress']} | seg: {current_segments}/{max_segments} | {'L' if loading else 'D'} |",end='\r')
        loading = False
    elif status == "pre_fetch":
        loading = True
    elif status == "post_fetch":
        max_segments = data['max_segments']
        current_segments = data['progress']
    elif status == "threaded":
        max_mb = data['max'] / (1024 * 1024)
        final_mb = data['final']
        downloaded_mb = data['progress'] / (1024 * 1024)
        done = data['done']
        finished = data['finished']
        max_seg = data['max_segments']
        print(f"| Downloaded: {downloaded_mb:.2f} MB |  Dumped: {max_mb:.2f}/~{final_mb} MB | thr: {threading.active_count()} | d:f: {done}:{finished}/{max_seg} |", end="\r")
        if done == finished and finished == max_seg:
            time.sleep(2)
            return "StopCallback" # code for stopping callback thread if running on threaded mode 
    time.sleep(0.2) # Required to block callback
```

To integrate this do:

```py
VideoFile = video.download(server_u=server, quality=quality, callback=getter)
```

This will allow you to view the download progress of the thread