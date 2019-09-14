from gevent import monkey
monkey.patch_all()

import gevent

import logging
import time
import os

import requests
import mistune

# TODO logger object - I can't get the log level working with that for some reason.
logging.getLogger().setLevel(logging.INFO)

FILENAME = "_test/README.md"

sess = requests.session()

class LinkExtractor(mistune.Renderer):
    def __init__(self):
        super().__init__()
        self.links = []

    # TODO empty impl of other methods?
    def link(self, link, title, text):
        self.links.append(link)

def main():
    start_time = time.time()
    links = extract_links(FILENAME)
    # TODO configure parallel
    #res = check_links(FILENAME, links)
    res = check_links_parallel(FILENAME, links)
    end_time = time.time()
    logging.info(f"elapsed time: {end_time-start_time}")
    return res


def extract_links(filename):
    # TODO resuse mistune instance and reset between runs
    link_finder = LinkExtractor()
    markdown = mistune.Markdown(renderer=link_finder)

    with open(filename) as f:
        contents = f.read()
    markdown(contents)
    # TODO dedupe links
    return link_finder.links

def check_link(base_file, link):
    if is_remote_link(link):
        return check_remote_link(link)
    else:
        return check_local_link(base_file, link)


def check_links(base_file, links):
    # TODO gevent to parallelize
    all_ok = True
    for l in links:
        is_ok = check_link(base_file, l)
        all_ok = all_ok and is_ok
        if is_ok:
            logging.info(f"ok: {l}")
        else:
            logging.warning(f"BAD: {l}")
    return all_ok


def check_links_parallel(base_file, links):
    links = set(links)
    jobs = {}
    for l in links:
        jobs[l] = gevent.spawn(check_link, base_file, l)
    gevent.joinall(jobs.values())
    all_ok = True
    for l, job in jobs.items():
        is_ok = job.get()
        all_ok = all_ok and is_ok

        if is_ok:
            logging.info(f"ok: {l}")
        else:
            logging.warning(f"BAD: {l}")
    return all_ok


def check_local_link(file, link):
    absfile = os.path.abspath(file)
    dir, _ = os.path.split(absfile)
    link_target = os.path.join(dir, link)
    # TODO allow dirs too (e.g. to localized docs)
    return os.path.isfile(link_target)

def check_remote_link(link):
    try:
        # TODO cache
        # TODO configurable timeout
        # TODO configure use session? reusing a session seems to help a bit but not a ton.
        resp = sess.get(link, timeout=5.0)
        # Any bad status (e.g. 4xx) will raise here
        resp.raise_for_status()
    except Exception as e:
        logging.warning(e)
        return False
    # Made it this far, so link must be OK
    return True


def is_remote_link(link: str):
    return link.startswith("http://") or link.startswith("https://")

if __name__ == "__main__":
    main()