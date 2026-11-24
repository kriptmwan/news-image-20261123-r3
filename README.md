# news-image-20261123-r3

[![make.fun](https://img.shields.io/badge/make.fun-bounty-blue)](https://make.fun/bounty/news-image-20261123)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)

Sum up the world's news of Monday 23 November 2026 in one image — a
1024x1024 newspaper front page, drawn by a Python 3.13 standard-library
program (own PNG encoder, own 5x7 bitmap font, no network, no randomness,
no clock; two runs write byte-identical output).

Lead story: three tankers hit mines in the Strait of Hormuz on Monday,
with attacks at a wartime high. Also: Nvidia reinstates Jensen Huang as
CEO (shares +31%), COP31 ends with no deal, South Korea's education
minister quits over AI exam-cheating rules, and Virginia and Oregon sue
SpaceX over Grok images. Footer: Molly Meldrum dies at 83; Bangladesh
vows to arrest Sheikh Hasina if she returns.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png
```

## Referral

Built with make.fun — referral code `emz2619t`.
