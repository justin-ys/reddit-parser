### imports ###
from PIL import Image
import requests
import json
from reddit_parse import mlplt_bargraph as bgraph
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
            if url.startswith("https://imgur"):
                url = url.replace("imgur.com", "i.imgur.com") + ".png"
            data = requests.get(url, stream=True).raw
            return Image.open(data)

        except (OSError, AttributeError) as e:
            log("Could not load image of post %s. Exception: %s" % (url, e))

        except requests.exceptions.ConnectionError as e:
            log("Timeout when trying to parse image of post %s. Exception: %s" % (url, e))

    return None  # We've either hit an error or a non-compliant post, so skip this one

#####################

### workers/main functions ###


def post_worker(post, ibase: list, name):
    """Given pushshift reddit post data,
    formats the post into
    the image template and saves it.
    Argument post: The pushshift JSON post data.
    Argument ibase: An array with the PIL image base as the
                    first argument, and a 4-tuple containing
                    the box to paste the extracted image
                    as the second argument
    Argument name: The name of the image to be saved."""

    base, pos = ibase[0], ibase[1]
    img = img_from_link(post['url'])
    if img is not None:
        if img.size[0] > 1214 or img.size[1] > 638:
            img = img.resize((1213, 637))
        blank = Image.new("RGBA", (1213, 637)) # why does Pillow force us to create another Image for pasting????
        blank.paste(img,
                    (int(round((blank.size[0]-img.size[0])/2)),
                     int(round((blank.size[1]-img.size[1])/2))))
        base.paste(blank, pos)
        base.save("out\\%s" % name)




