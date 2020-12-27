### imports ###
from tqdm import tqdm
from PIL import Image, ImageFont, ImageDraw
import requests
import numpy
import json
import datetime
import codecs
import time
import multiprocessing as mp
from functools import partial
import sys
from reddit_parse import mlplt_bargraph as bgraph


###############


### functions/libs ###

def log(text: str, fname: str):
    with codecs.open(fname, "a", "utf-8-sig") as f:
        f.write("\n" + text)


def pushshift_get(subs, stime, etime):
    # slightly based on https://gist.github.com/dylankilkenny/3dbf6123527260165f8c5c3bc3ee331b, so thanks
    posts = []
    for sub in subs:
        response = requests.get("https://api.pushshift.io/reddit/search/submission?"
                                "&before=%s"
                                "&after=%s"
                                "&subreddit=%s"
                                "&size=100000"  # otherwise just returns 25
                                % (etime, stime, sub))
        posts.extend(json.loads(response.text)['data'])
    return sorted(posts, key = lambda post: post['created_utc'])


def get_providers():
    with open("trusted_providers.txt", 'r')as f:
        data = f.read()
        return tuple(data.split("\n"))


def img_from_post(post: dict):
    url = post['url']
    if url.startswith(get_providers()):
        try:
            if url.startswith("https://imgur"):
                url = url.replace("imgur.com", "i.imgur.com") + ".png"
            data = requests.get(url, stream=True).raw
            return Image.open(data)

        except (OSError, AttributeError) as e:
            log("Could not load image of post %s. Exception: %s" % (url, e), "logs/log.txt")

        except requests.exceptions.ConnectionError as e:
            log("Timeout when trying to parse image of post %s. Exception: %s" % (url, e), "logs/log.txt")


    return None  # We've either hit an error or a non-compliant post, so skip this one


#####################

### workers/main functions ###


def post_worker(args, ibase):
    """Given pushshift reddit post data,
    formats the post into
    the image template and saves it.
    Argument args: A tuple with the pushshift JSON post data
                    as the first element, the number of the
                    post as the second element and the karma
                    leaderboard graph as the third element.
                    (multiprocessing reasons)
    Argument ibase: An array with the PIL image base as the
                    first argument, and a 4-tuple containing
                    the box to paste the extracted image
                    as the second argument
                    """
    post, name, graph = args[0], args[1], args[2]

    def get_text_centered(text, font, size, loc):
        fnt = ImageFont.truetype(font, size, encoding='unic')
        size = fnt.getsize(text)
        return loc - size[0] / 2

    base, pos = ibase[0], ibase[1]
    base_new = base.copy()
    img = img_from_post(post)
    if img is not None:
        target_x = pos[2] - pos[0]
        target_y = pos[3] - pos[1]
        if img.size[0] > target_x or img.size[1] > target_y:
            img.thumbnail((target_x, target_y))
        blank = Image.new("RGB",
                          (target_x, target_y))  # why does Pillow force us to create another Image for pasting???
        blank.paste(img,
                    (int(round((blank.size[0] - img.size[0]) / 2)),
                     int(round((blank.size[1] - img.size[1]) / 2))))
        base_new.paste(blank, pos)

        # Drawing the text.....
        draw = ImageDraw.Draw(base_new)
        titlepos = get_text_centered(post['title'], "reddit_parse/resources/symbola.ttf", 108, 2076)
        authpos = get_text_centered("by /u" + post['author'], "reddit_parse/resources/symbola.ttf", 48, 2060)
        scorepos = get_text_centered("karma:" + str(post['score']), "reddit_parse/resources/symbola.ttf", 36, 2060)

        tfont = ImageFont.truetype("reddit_parse/resources/symbola.ttf", 108, encoding='unic')
        draw.text((titlepos, 520), post['title'], font=tfont, fill=(0, 0, 0, 255))

        afont = ImageFont.truetype("reddit_parse/resources/symbola.ttf", 48, encoding='unic')
        draw.text((authpos, 670), "by /u/" + post['author'], font=afont, fill=(0, 0, 0, 255))

        sfont = ImageFont.truetype("reddit_parse/resources/symbola.ttf", 36, encoding='unic')
        if post['score'] > 0:
            draw.text((scorepos, 832), "karma: " + str(post['score']), font=sfont, fill=(255, 139, 96, 255))
        else:
            draw.text((scorepos, 832), "karma: " + str(post['score']), font=sfont, fill=(148, 148, 255, 255))

        draw.text((30, 220), datetime.datetime.utcfromtimestamp(post['created_utc']).strftime("%B %d, %Y %H:%M:%S"),
                  font=sfont, fill=(0, 0, 0, 255))
        base_new.paste(graph, (0, base.size[1] - graph.size[1]))
        base_new.save("out/parsed_%s.png" % str(name).zfill(6))


def subreddit_worker(sub, stime, etime, timg):
    """Given a subreddit and a start time,
    parses every post through post_worker.
    Argument sub: The subreddit name, as a string.
    Argument stime: The time to start in epoch time, as a string.
    Argument etime: The time to end in epoch time, as a string
    Argument timg: See ibase in post_worker"""
    times = numpy.arange(stime, etime, 3600)
    leaderboard = {}
    leaderboard_old = 0
    graph = bgraph.graph_names([""] * 3, [0] * 3)
    count = 0
    glist = []
    for i in range(0, len(times)):
        print("Now processing: Block %d out of %d" % (i, len(times) - 1))
        try:
            data = pushshift_get(sub, times[i], times[i + 1])

        except IndexError:
            data = pushshift_get(sub, times[-1], int(time.time()))

        except (requests.ConnectionError, requests.ConnectTimeout):
            print("Connection error, sleeping for 10 minutes")
            log("Could not connect to pushshift at %s on post %s" % (datetime.datetime.now(), count))
            time.sleep(600)
            data = pushshift_get(sub, times[i], times[i + 1])

        print("graphing karma....")
        for post in data:
            if post['author'] != "[deleted]":
                try:
                    leaderboard[post['author']] += post['score']
                except KeyError:
                    leaderboard[post['author']] = post['score']

            leaderboard_top = sorted(leaderboard, key=leaderboard.get)[-3:]
            if leaderboard_top != leaderboard_old:
                glist.append(bgraph.graph_names(leaderboard_top, [leaderboard[x] for x in leaderboard_top],
                                                "Karma Leaderboard"))
                leaderboard_old = leaderboard_top
            else:
                glist.append(glist[-1])

            log(u"Post %s at %s by /u/%s. Score: %s\n" % (
                post['permalink'], post['created_utc'], post['author'], post['score']), "logs/record.txt")

        print("Done, now parsing posts")

        #TODO: below uses multiprocessing for post rendering, runs fast but wow please redo it i'm sure it can look better than this
        with mp.Pool(processes=5) as pool:
            with tqdm(total=len(data)) as pbar:  # it's about to get ugly....
                for i, _ in enumerate(pool.imap_unordered(partial(post_worker, ibase=timg),
                                    zip(data, range(count, count + len(data)), glist))):
                    pbar.update()

            count += len(data)


if __name__ == '__main__':
    subs = sys.argv[1].split(",")
    start_time = int(sys.argv[2])
    end_time = int(sys.argv[3])
    template = [Image.open("reddit_parse/resources/template.png"), (35, 258, 1595, 1080)]
    subreddit_worker(subs, start_time, end_time, template)
