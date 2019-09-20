from gevent import monkey  # noqa
monkey.patch_all()  # noqa

import argparse
import mistune
import requests
import os
import time
import logging
import gevent


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


def main(files_to_check, links_to_exclude):
    links_to_exclude = set(links_to_exclude or [])
    # TODO filter excluded links
    start_time = time.time()
    all_ok = True
    for f in files_to_check:
        links = extract_links(f)
        # TODO configure parallel
        res = check_links_parallel(f, links)
        all_ok = all_ok and res
    end_time = time.time()
    logging.info(f"elapsed time: {end_time-start_time}")
    return all_ok


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
    # TODO optimize with a single os.stat call?
    return os.path.isfile(link_target) or os.path.isdir(link_target)


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
    # TODO use https://validators.readthedocs.io/en/latest/#module-validators.url
    return link.startswith("http://") or link.startswith("https://")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+')
    parser.add_argument("--exclude", action='append',
                        help="Links to exclude from checking.")
    args = parser.parse_args()

    print(args)

    res = main(args.files, args.exclude)
    import sys
    sys.exit(0 if res else 1)
