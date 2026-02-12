# Web Novel to EPUB
Modular multithreaded online novel parser and downloader. This tool converts popular websites to a locally stored epub ebook file.

## Features
- **Plugin-based parsing**: Easy to add support for more websites \[[Supported Sites](#supported-sites)\]
- **Multithreaded downloads**: Concurrent downloads
- **Rolling release support**: Update epubs with only new chapters to save time and bandwidth
- **Full EPUBs**: epubs include covers, table of contents, and all relevant metadata

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Lukas-DS/Web-Novel-to-EPUB.git
cd Web-Novel-to-EPUB
```
### 2. Dependencies
#### With pip
install dependencies from requirements.txt with pip
```bash
pip install -r requirements.txt
```

#### With poetry
install dependencies with poetry
```bash
poetry install
```

## Usage
Basic usage
`python main.py "https://example-novel-site.com/novel-title"`

### Arguments

| Argument | Description |
|------|------|
| `-h`, `--help` | Gives more information about commands |
| `-y`, `--yes` | Skip all confirmation prompts |
| `-o [path]`, `--output [path]` | Specify a base directory for downloads |
| `--no-download` | Skip the download phase (only use when archive is up to date) |
| `--no-parse` | Skip the parsing phase (only use when archive is up to date) |
| `--no-cover` | Do not download or include a cover image |
| `--no-missing` | Do not add "Missing Chapter" placeholder pages to the EPUB |

## Supported Sites
| Site |
|-----|
| `wattpad` |
| `readernovel` | 
| `lightnovelworld` |
| `readnovelfull` |

## Development
### Adding sources/parsers
1. Create a new parser class off of the abstract class in parser.py
2. Drop the new class into parsers and you're good.

Make sure parsers meet all class requirements.
Example parsers exist in `parsers/`

### Adding packages
`poetry add package`
