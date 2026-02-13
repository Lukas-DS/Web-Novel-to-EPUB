# for base code
import zipfile, os, json, re, argparse, sys
from ebooklib import epub
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from bs4 import BeautifulSoup

# for dynamic parsers
import importlib, pkgutil, inspect, modules
import parsers
from parser import Parser

def get_parsers():
    """Imports all parsers and returns a list of class names"""
    classes = []
        # scanning through the "package" in parsers/
    for _, module_name, _ in pkgutil.iter_modules(parsers.__path__):
        module = importlib.import_module(f"{parsers.__name__}.{module_name}")

        for name, obj in inspect.getmembers(module, inspect.isclass):

            if obj.__module__ != module.__name__:
                continue

            if (
                obj.__module__ == module.__name__
                and issubclass(obj, Parser)
                and not inspect.isabstract(obj)
            ):
                classes.append(obj)
    return classes

def get_parser(identifier):
    """
    finds parser required from list of parsers
    """
    classes = get_parsers()

    # check to compare identifier and class name
    for c in classes:
        if c.name in identifier:
            return c

    # attribute error if no matches
    raise AttributeError(f"no matching classes")


def path_setup(base, novel_title, parser_name):
    """Basic setup for paths"""

    # Remove special chars
    folder_name = re.sub(r'[\\/*?:"<>|]', "", f"{novel_title}_{parser_name}")
    full_path = os.path.join(base, folder_name)

    os.makedirs(full_path, exist_ok=True)

    return {
        "dir": full_path,
        "raw_zip": os.path.join(full_path, "raw_chapters.zip"),
        "parsed_zip": os.path.join(full_path, "parsed_chapters.zip"),
        "info": os.path.join(full_path, "info.json"),
        "metadata": os.path.join(full_path, "metadata.json"),
        "epub": os.path.join(full_path, f"{novel_title}.epub"),
    }


def print_bar(current_index, digits):
    """takes in an int: index int:digits\nreturns a string with str(current_index) with digits length\nEx. print_bar(10, 4) -> '0010'"""
    append = "0" * (digits - len(str(current_index)))
    return append + str(current_index)


def parse_worker(zfo, chn, parser, blacklist):
    print(f"parsing chap: {print_bar(chn, 5)}", end="\r")
    filename = f"{chn}.chapter"
    html = zfo.read(filename).decode("utf-8")
    title, body = parser.parse_chapter(html, blacklist)
    return chn, title, body


def parsing(zip_name_A, zip_name_B, metadata, keys, parser, blacklist):
    """
    Takes in:
        zip_name_A: location of zip file with raw chapter html
        zip_name_B: location where zip file with parsed chapter htmls will be placed
        metadata: dict containing chapter titles
        keys: key names to be parsed from zip_name_A
    Output:
        metadata: dict containing chapter titles updated with new info
    """
    print("beginning parsing")

    with zipfile.ZipFile(zip_name_A, "r") as zfo, zipfile.ZipFile(
        zip_name_B, "a", compression=zipfile.ZIP_DEFLATED
    ) as zfn:

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(parse_worker, zfo, chn, parser, blacklist) for chn in keys]

            for fut in as_completed(futures):
                chn, title, body = fut.result()
                zfn.writestr(f"{chn}.chapter", body_list_to_html(title, body))
                metadata[chn] = title
    print()
    print("finished parsing")
    return metadata

def body_list_to_html(title, body):
    body_html = f"<h1>{title}</h1>\n" "<p>" + "</p><p>".join(body) + "</p>"
    return body_html

def dl_chapter(i, zf, links, parser, zip_lock):
    """Downloads chapter i from homepage['links'] writes it into zip file zf"""
    print(f"Downloading CH: {print_bar(i, 5)}", end="\r")

    if i not in links:
        print(f"Skipping missing chapter {i}")
    else:
        filename = f"{i}.chapter"
        data = parser.grab(links[i])
        with zip_lock:
            zf.writestr(filename, data)


def get_args():
    parser = argparse.ArgumentParser(
        description="Scrape web novels from various sources and convert them to EPUB."
    )

    # The URL is a required arg
    parser.add_argument("url", help="The homepage URL of the novel")

    parser.add_argument(
        "--parsers",
        action="store_true",
        help="List all the parsers currently available",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="novel_out",
        help="specify output directory (default: novel_out)",
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip all confirmation prompts (auto-confirm 'yes')",
    )

    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Skip the downloading step (only do if you know archive is up to date with source)",
    )

    parser.add_argument(
        "--no-parse",
        action="store_true",
        help="Skip the parsing step (only do this if you know archive is up to date with source)",
    )

    parser.add_argument(
        "--no-missing",
        action="store_true",
        help="Doesn't add pages indicated a missing chapter to the epub file",
    )

    parser.add_argument(
        "--no-cover",
        action="store_true",
        help="Doesn't download or add cover to epub",
    )

    return parser.parse_args()


def main():
    # getting blacklist from blacklist.txt
    # each line has a blacklisted phrase
    BLACKLIST = []
    with open("blacklist.txt", "r") as f:
        for line in f:
            BLACKLIST.append(line)

    BLACKLIST_RE = re.compile(
        r"(?:%s)" % "|".join(map(re.escape, BLACKLIST)), flags=re.IGNORECASE
    )

    zip_lock = Lock()

    args = get_args()
    
    if args.parsers:
        for parser in get_parsers():
            print(parser.name)
        sys.exit(1)

    ParserClass = get_parser(args.url)
    parser = ParserClass()

    homepage = parser.parse_homepage(args.url)
    paths = path_setup(args.output, homepage["title"], parser.name)

    print(
        f"""-----------
\tLanguage: {homepage["language"]}
\t{homepage["title"]} - {homepage["author"]}
\t{homepage["description"][:30]+'...' if len(homepage["description"]) > 30 else homepage["description"]}
\tLast Chapter: {homepage["last"]}
\tTotal Chapters: {len(homepage["links"])}
-----------"""
    )

    # file name assignments
    zip_name_A = paths["raw_zip"]
    homepage_file_name = paths["info"]
    zip_name_B = paths["parsed_zip"]
    metadata_file_name = paths["metadata"]

    def account_for_missing(last, links, accounted):
        still_missing = []
        for i in range(1, last + 1):
            if not i in links:
                # accounted logic broken rn (pray that website doesn't replace missing chapts)
                # if i in accounted:
                #    continue
                still_missing.append(i)
        return still_missing

    # have keys_to_download contain only new chaps keys
    # works by removing the old keys from the new keys
    if os.path.isfile(zip_name_A) and os.path.isfile(homepage_file_name):
        print("\tArchive found - Checking for updates")
        print("-----------")

        with open(homepage_file_name, "r") as f:
            data = json.loads(
                f.read(),
                object_hook=lambda d: {
                    int(k) if k.lstrip("-").isdigit() else k: v for k, v in d.items()
                },
            )
        homepage["missing"] = account_for_missing(
            homepage["last"], homepage["links"], data["missing"]
        )

        print("-----------")
        print("Archive has: ")
        print(f"\tLast Chapter: {data["last"]}")
        print(f"\tTotal Chapters: {len(data["links"])}")
        if (data["last"] == homepage["last"]) and (data["links"] == homepage["links"]):
            print("\tArchive up to date")
            keys_to_download = set()
        else:
            print("\tArchive not up to date")
            keys_to_download = set(homepage["links"].keys() - data["links"].keys())
        print("-----------")
    else:
        print("\tNo archive found - No missing accounted for")
        print("-----------")

        keys_to_download = homepage["links"].keys()
        homepage["missing"] = account_for_missing(
            homepage["last"], homepage["links"], []
        )

        print(
            f"\tMissing chapters: {"None" if not homepage["missing"] else homepage["missing"]}"
        )
        print("-----------")

    keys_to_download = list(keys_to_download)

    print(f"\tTo download: {len(keys_to_download)} chapters")

    if args.yes or args.no_download:
        print("Continuing to download")
    else:
        print("Proceed to downloading?")
        userin = input()
        if userin == "y":
            print("Continuing to download")
        else:
            print("Exiting")
            sys.exit(1)

    # Step 1 - download all the chapters and put them in a zip file (A)

    # add a check if to_download exists if not ask for skip
    if keys_to_download == []:
        print("Nothing to do; Skipping downloads")
    elif args.no_download:
        print("Skipping downloads (could cause errors)")
    else:
        # create/append to zip file using multithreaded parsers
        with zipfile.ZipFile(zip_name_A, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            with ThreadPoolExecutor(max_workers=parser.max_clients) as executor:
                list(
                    executor.map(
                        lambda i: dl_chapter(i, zf, homepage["links"], parser, zip_lock), keys_to_download
                    )
                )
    print()
    print("-----------")

    # Cover image handler
    image_ext = "." + homepage["image"].split(".")[-1]
    image_path = os.path.join(paths["dir"], f"cover{image_ext}")

    if args.no_cover:
        print("Skipping cover")
    elif os.path.isfile(image_path):
        print("Cover exists")
    else:
        print("Downloading cover image")
        req = parser.grab(homepage["image"], raw=True)
        with open(image_path, "wb") as f:
            f.write(req.content)

    # write homepage to disk for future use
    with open(homepage_file_name, "w") as f:
        f.write(json.dumps(homepage))

    # Step 2 - process the files in (A) and put into a new zip (B)

    # check for archived data already parsed
    if os.path.isfile(metadata_file_name):
        print("\tmetadata found successfully")

        # quick convert from json to python dict
        with open(metadata_file_name, "r") as f:
            metadata = json.loads(
                f.read(),
                object_hook=lambda d: {
                    # converts string key names to int
                    int(k) if k.lstrip("-").isdigit() else k: v
                    for k, v in d.items()
                },
            )

        # parsed archive found, only need to parse new chapters
        keys_to_parse = keys_to_download
    else:
        print("\tno previous metadata found...")
        metadata = {}
        # if theres no metadata, no parsed archive exists
        # keys_to_parse must include all chapters
        keys_to_parse = list(homepage["links"].keys())

    print(f"\tTo parse: {len(keys_to_parse)}")

    # Check for continuing with parsing
    if args.yes:
        print("Continuing to parse")
    else:
        print("Proceed to parsing?")
        userin = input()
        if userin == "y":
            print("Continuing to parse")
        else:
            print("Exiting")
            sys.exit(1)

    if keys_to_parse == []:
        print("Nothing to parse; skipping parsing")
    elif args.no_parse:
        print("Skipping parse (could cause errors)")
    else:
        metadata = parsing(zip_name_A, zip_name_B, metadata, keys_to_parse, parser, BLACKLIST_RE)

    print("-----------")

    # write metadata so parsing won't be repeated
    with open(metadata_file_name, "w") as f:
        f.write(
            json.dumps(metadata)
        )  # maybe delete metadata cause need to re-soup all files anyways

    # Step 3 - combine files in parsed archive into a epub file

    if args.yes:
        print("Continuing to build epub")
    else:
        print("Proceed to building epub?")
        userin = input()
        if userin == "y":
            print("Continuing to build epub")
        else:
            print("Exiting")
            sys.exit(1)

    book = epub.EpubBook()

    book.set_title(homepage["title"])
    book.set_language(homepage["language"])
    book.add_author(homepage["author"])
    book.add_metadata("DC", "description", homepage["description"])

    if not args.no_cover and os.path.isfile(image_path):
        book.set_cover(f"cover{image_ext}", open(image_path, "rb").read())
    else:
        print("no cover")

    # Ensure correct version of metadata is loaded
    with open(metadata_file_name, "r") as f:
        metadata = json.loads(f.read())

    chapter_list = []

    # Reading from parsed archive and building epub
    # memory heavy step, all chapters must be stored in memory
    with zipfile.ZipFile(zip_name_B, "r") as zf:
        for i in range(1, homepage["last"] + 1):
            print(f"building ch for ch {print_bar(i, 5)}", end="\r")
            if i in homepage["missing"]:
                if args.no_missing:
                    print("ignoring missing", i)
                    continue
                print()
                print("missing chap", i)
                ch_t = f"Chapter {i}: Missing"
                ch_b = f"<h1>Missing Chapter {i}</h1><p>No content found for ch:{i}</p><p>I suggest you look for it online</p><p><a href=\"https://www.google.com/search?q={homepage['title']}+chapter+{i}\" rel=\"noreferrer\">search on google</a></p>"
            else:
                filename = f"{i}.chapter"
                html = zf.read(filename).decode("utf-8")
                ch_b = html
                ch_t = metadata[str(i)]

            ch = epub.EpubHtml(title=ch_t, file_name=f"{i}.xhtml")
            ch.content = ch_b
            book.add_item(ch)
            chapter_list.append(ch)
    print()
    print("finised added chapters")
    clt = tuple(chapter_list)
    book.toc = clt
    cln = ["nav"]
    for item in chapter_list:
        cln.append(item)
    book.spine = cln
    book.add_item(epub.EpubNav())

    epub.write_epub(paths["epub"], book)
    print("Book written successfully")
    print("============")
    print(os.path.abspath(paths["epub"]))
    print("============")


if __name__ == "__main__":
    main()
