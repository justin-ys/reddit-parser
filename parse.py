### imports ###
import praw
from PIL import Image
import requests
from reddit_parse import mlplt_bargraph
###############


### functions/libs ###
def record(text: str):
    with open("logs\\datalog.txt", "a") as f:
        f.write("\n" + text)


def log(text: str):
    with open("logs\\log.txt", "a") as f:
        f.write("\n" + text)


def get_providers():
    with open("trusted_providers.txt", 'r')as f:
        data = f.read()
        return tuple(data.split("\n"))


def img_from_link(url):
    if url.startswith(get_providers()):
        try:
            data = requests.get(url, stream=True)
            return Image.open(data)

        except OSError as e:
            log("Could not load image of post %s. Exception: %s" % (url, e))

        except requests.exceptions.ConnectionError as e:
            log("Timeout when trying to parse image of post %s. Exception: %s" % (url, e))
