### imports ###
from PIL import Image, ImageFont, ImageDraw
import requests
import numpy
import json
import time
from reddit_parse import mlplt_bargraph as bgraph
###############


### functions/libs ###

def log(text: str, fname: str):
    with open(fname, "a") as f:
        f.write("\n" + text)


def pushshift_get(sub, stime, etime):
    # slightly based on https://gist.github.com/dylankilkenny/3dbf6123527260165f8c5c3bc3ee331b, so thanks
    response = requests.get("https://api.pushshift.io/reddit/search/submission?"
                            "&before=%s"
                            "&after=%s"
                            "&subreddit=%s"
                            % (etime, stime, sub))
    return json.loads(response.text)['data']

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
            log("Could not load image of post %s. Exception: %s" % (url, e),"logs\\log.txt")

        except requests.exceptions.ConnectionError as e:
            log("Timeout when trying to parse image of post %s. Exception: %s" % (url, e),"logs\\log.txt")

    return None  # We've either hit an error or a non-compliant post, so skip this one

#####################

### workers/main functions ###


def post_worker(post, ibase: list, name, graph):
    """Given pushshift reddit post data,
    formats the post into
    the image template and saves it.
    Argument post: The pushshift JSON post data.
    Argument ibase: An array with the PIL image base as the
                    first argument, and a 4-tuple containing
                    the box to paste the extracted image
                    as the second argument
    Argument name: The name of the image to be saved.
    Argument graph: An image containing a bargraph for karma scores."""
    def get_text_centered(text, font, size, pos):
        fnt = ImageFont.truetype(font, size, encoding='unic')
        size = fnt.getsize(text)
        return pos - size[0]/2

    base, pos = ibase[0], ibase[1]
    base_new = base.copy()
    img = img_from_link(post['url'])
    if img is not None:
        target_x = pos[2] - pos[0]
        target_y = pos[3] - pos[1]
        if img.size[0] > target_x or img.size[1] > target_y:
            img = img.resize((target_x, target_y))
        blank = Image.new("RGB", (target_x, target_y)) # why does Pillow force us to create another Image for pasting???
        blank.paste(img,
                    (int(round((blank.size[0]-img.size[0])/2)),
                     int(round((blank.size[1]-img.size[1])/2))))
        base_new.paste(blank, pos)

        # Drawing the text.....
        draw = ImageDraw.Draw(base_new)
        titlepos = get_text_centered(post['title'], "reddit_parse\\resources\\symbola.ttf",108,2076)
        authpos = get_text_centered("by /u" + post['author'], "reddit_parse\\resources\\symbola.ttf", 48, 2060)
        scorepos = get_text_centered("karma:" + str(post['score']), "reddit_parse\\resources\\symbola.ttf", 36, 2060)

        tfont = ImageFont.truetype("reddit_parse\\resources\\symbola.ttf", 108, encoding='unic')
        draw.text((titlepos, 520), post['title'], font=tfont, fill=(0,0,0,255))

        afont = ImageFont.truetype("reddit_parse\\resources\\symbola.ttf", 48, encoding='unic')
        draw.text((authpos, 670), "by /u/" + post['author'], font=afont, fill=(0,0,0,255))

        sfont = ImageFont.truetype("reddit_parse\\resources\\symbola.ttf", 36, encoding='unic')
        if post['score'] > 0:
            draw.text((scorepos, 832), "karma: " + str(post['score']), font=sfont, fill=(255,139,96,255))
        else:
            draw.text((scorepos, 832), "karma: " + str(post['score']), font=sfont, fill=(148,148,255,255))

        base_new.paste(graph, (0,base.size[1] - graph.size[1]))
        log("Post %s at %s by /u/%s. Score: %s\n" % (post['permalink'], post['created_utc'], post['author'], post['score']), "logs\\record.txt")
        base_new.save("out\\%s" % name)

def subreddit_worker(sub, stime, etime, timg):
    """Given a subreddit and a start time,
    parses every post through post_worker.
    Argument sub: The subreddit name, as a string.
    Argument stime: The time to start in epoch time, as a string.
    Argument etime: The time to end in epoch time, as a string
    Argument timg: See ibase in post_worker"""
    times = numpy.arange(stime, etime, 3600) # implement your gnown gnarange function CHUM
    leaderboard = {}
    leaderboard_old = 0
    graph = bgraph.graph_names([""] * 3, [0] * 3)
    try:
        count = 0
        for i in range(0,len(times)):
            data = pushshift_get(sub,times[i],times[i+1])
            for post in data:
                if post['author'] is not "[deleted]":
                    try:
                        leaderboard[post['author']] += post['score']
                    except KeyError:
                        leaderboard[post['author']] = post['score']

                leaderboard_top = sorted(leaderboard, key=leaderboard.get)[-3:]
                if leaderboard_top != leaderboard_old:
                    graph = bgraph.graph_names(leaderboard_top, [leaderboard[x] for x in leaderboard_top],"Karma Leaderboard")
                    leaderboard_old = leaderboard_top
                post_worker(post, timg, "parsed_%s.png" % str(count).zfill(6), graph)
                count += 1
    except IndexError:
        data = pushshift_get(sub, times[-1], int(time.time()))
        for post in data:
            post_worker(post, timg, "parsed_%s.png" % str(count).zfill(6), graph)






if __name__ == '__main__':
    template = [Image.open("reddit_parse\\resources\\template.png"),(35,258,1595,1080)]
    subreddit_worker('me_irl', 1514764800, 1514779800, template)