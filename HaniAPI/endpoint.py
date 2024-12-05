from CFSession import cfDirectory
class Targets:
    directory = cfDirectory(cache_path=".browser/hanime")

class PreData:
    #Use lambda to prevent data override
    search_post = lambda: {"search_text":"","tags":[],"tags_mode":"AND","brands":[],"blacklist":[],"order_by":"created_at_unix","ordering":"desc","page":0}

class Site:
    auth = "https://hanime.tv/sign-in"
    api_auth = "https://www.universal-cdn.com/rapi/v4/sessions"
    api_coins = "https://www.universal-cdn.com/rapi/v4/coins"
    home = "https://hanime.tv/"
    account = "https://hanime.tv/account"
    trending_monthly = "https://hanime.tv/browse/trending"
    search_api = "https://search.htv-services.com"
    search_v7 = "https://hanime.tv/rapi/v7/search"
    video_page = "https://hanime.tv/videos/hentai"
    video_v7 = "https://hanime.tv/rapi/v7/video" #?id={slug}
     
