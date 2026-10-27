import argparse
from . import fabriquer, NOMS

parser = argparse.ArgumentParser(description="Services publics en lecture seule")
parser.add_argument("connecteur", choices=NOMS)
fabriquer(parser.parse_args().connecteur).run(transport="stdio", show_banner=False)
