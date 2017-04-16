# Installation

Clone recursively to also get required submodules.

`git clone --recursive https://github.com/dagurval/bip100.tech`

# Update vote information

- Requires a BIP100 node running.
- Node must be configured with txindex=1
- RPC username and password are assumed to be located at ../.bitcoin/bitcoin.conf

Run bip100-json.py to generate json data used by the website. The script will
add update json files in location ./web/period

# The website

The website itself consists of only static files. Point the webserver to serve
files in folder web/

