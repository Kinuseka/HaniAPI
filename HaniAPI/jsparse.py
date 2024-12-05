import json, re
from bs4 import BeautifulSoup
def parse_js(soups):
    c = None
    if len(soups) > 1:
        for soup in soups: #dynamically guess the API 
            try:
                extracted = soup.contents[0].strip().replace("window.__NUXT__=", "")
                extracted = re.split(";$",extracted)[0]
                c = json.loads(extracted)
                break
            except json.decoder.JSONDecodeError:
                pass
            except IndexError:
                pass
    else:
        extracted = soups.contents[0].strip().replace("window.__NUXT__=", "")
        extracted = re.split(";$",extracted)[0]
        c = json.loads(extracted)
    return c

def full_parser(html_string):
    return parse_js(BeautifulSoup(html_string, 'html.parser').find_all("script"))

    