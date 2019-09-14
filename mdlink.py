FILENAME = "_test/README.md"

import mistune

class LinkExtractor(mistune.Renderer):
    def __init__(self):
        super().__init__()
        self.links = []

    # TODO empty impl of other methods?
    def link(self, link, title, text):
        self.links.append(link)

def main():
    extract_links(FILENAME)

def extract_links(filename):
    # TODO resuse mistune instance and reset between runs
    link_finder = LinkExtractor()
    markdown = mistune.Markdown(renderer=link_finder)

    with open(filename) as f:
        contents = f.read()
        markdown(contents)
        print(link_finder.links)

def check_local_link(file, link):
    pass

def check_remote_link(link):
    pass

def is_remote_link(link: str):
    return link.startswith("http://") or link.startswith("https://")

if __name__ == "__main__":
    main()