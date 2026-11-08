"""Ordinary Python estimate CLI; explicit price scenario, never a live-price claim.

Reads --quantities JSON and --rates JSON, writes costs.csv, estimate.json and
estimate.html into --output FRESH_DIR. Standard library only; no network/orders.
The bundled USD scenario is a dated example that requires refresh for new quotes.
"""
import argparse
from pathlib import Path
from building_study.runtime import output_path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quantities',required=True,type=Path)
    parser.add_argument('--rates',required=True,type=Path)
    parser.add_argument('--output',required=True,type=output_path)
    from building_study.price_budget import main as price
    price(parser.parse_args())

if __name__=='__main__':main()
