from gevent import monkey  # noqa
monkey.patch_all()  # noqa

import argparse
import mistune
import requests
import os
import time
import logging
import gevent

from typing import List, Iterable


# TODO logger object - I can't get the log level working with that for some reason.
logging.getLogger().setLevel(logging.INFO)

FILENAME = "_test/README.md"

sess = requests.session()


class LinkExtractor(mistune.Renderer):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    # TODO empty impl of other methods?
    def link(self, link: str, title: str, text: str) -> None:
        self.links.append(link)


def check_all_links(files_to_check: List[str], links_to_exclude: Iterable[str] = None) -> bool:
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


def extract_links(filename: str) -> List[str]:
    # TODO resuse mistune instance and reset between runs
    link_finder = LinkExtractor()
    markdown = mistune.Markdown(renderer=link_finder)

    with open(filename) as f:
        contents = f.read()
    markdown(contents)
    # TODO dedupe links
    return link_finder.links


def check_link(base_file: str, link: str) -> bool:
    if is_remote_link(link):
        return check_remote_link(link)
    else:
        return check_local_link(base_file, link)


def check_links(base_file: str, links: List[str]) -> bool:
    all_ok = True
    for l in links:
        is_ok = check_link(base_file, l)
        all_ok = all_ok and is_ok
        if is_ok:
            logging.info(f"ok: {l}")
        else:
            logging.warning(f"BAD: {l}")
    return all_ok


def check_links_parallel(base_file: str, links: Iterable[str]) -> bool:
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


def check_local_link(file: str, link: str) -> bool:
    absfile = os.path.abspath(file)
    dir, _ = os.path.split(absfile)
    link_target = os.path.join(dir, link)
    # TODO optimize with a single os.stat call?
    return os.path.isfile(link_target) or os.path.isdir(link_target)


def check_remote_link(link: str) -> bool:
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


def is_remote_link(link: str) -> bool:
    # TODO use https://validators.readthedocs.io/en/latest/#module-validators.url
    return link.startswith("http://") or link.startswith("https://")


def main() -> bool:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+')
    parser.add_argument("--exclude", action='append', help="Links to exclude from checking.")
    args = parser.parse_args()

    res = check_all_links(args.files, args.exclude)
    return res


if __name__ == '__main__':
    exit(main())
