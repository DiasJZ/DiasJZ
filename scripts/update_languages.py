"""Render public, non-fork repository language bytes as a dependency-free SVG.

The profile repository is excluded so this script does not distort the chart.
Run: python scripts/update_languages.py
Offline preview: python scripts/update_languages.py --data snapshot.json
"""
import argparse
from collections import Counter
from html import escape
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COLORS = {"Java": "#E5A26B", "JavaScript": "#F1D86A", "TypeScript": "#4E9BD0",
          "CSS": "#AD91E8", "HTML": "#EF876A", "Python": "#5EA9B5",
          "PHP": "#929CD0", "Shell": "#94BD80", "Outras": "#84929E"}


def api(path):
    headers = {"User-Agent": "DiasJZ-profile-languages", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def collect(owner):
    data = {}
    page = 1
    while True:
        repos = api(f"/users/{owner}/repos?type=owner&per_page=100&page={page}")
        for repo in repos:
            if repo["private"] or repo["fork"] or repo["name"].casefold() == owner.casefold():
                continue
            data[repo["full_name"]] = api(f'/repos/{repo["full_name"]}/languages')
        if len(repos) < 100:
            return data
        page += 1


def render(data):
    totals = Counter()
    for languages in data.values():
        totals.update({name: size for name, size in languages.items() if size > 0})
    entries = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    if len(entries) > 7:
        entries = entries[:7] + [("Outras", sum(size for _, size in entries[7:]))]
    total = sum(totals.values())
    count = sum(bool(langs) for langs in data.values())
    height = max(330, 120 + 37 * len(entries))
    cy = height / 2 + 15
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{height}" viewBox="0 0 800 {height}" role="img" aria-labelledby="title desc">',
           '<title id="title">Linguagens nos meus repositórios</title>',
           '<desc id="desc">Distribuição por bytes de código em repositórios públicos próprios. ' + escape(", ".join(f"{n}: {v / total:.1%}" for n, v in entries) if total else "Ainda sem código detectado.") + '</desc>',
           f'<rect x=".5" y=".5" width="799" height="{height - 1}" rx="18" fill="#101923" stroke="#2B4050"/>',
           '<g font-family="Segoe UI,Arial,sans-serif">',
           '<text x="34" y="43" fill="#E5A26B" font-size="21" font-weight="600">Linguagens em código</text>',
           '<text x="34" y="69" fill="#94A6B6" font-size="13">Uma visão do que construo no GitHub</text>',
           f'<circle cx="182" cy="{cy}" r="87" fill="none" stroke="#203240" stroke-width="28"/>']
    offset = 0
    circumference = 2 * math.pi * 87
    for index, (name, size) in enumerate(entries):
        share = size / total
        length = share * circumference
        color = COLORS.get(name, ["#68B6A5", "#94BD80", "#929CD0"][index % 3])
        svg.append(f'<circle cx="182" cy="{cy}" r="87" fill="none" stroke="{color}" stroke-width="28" stroke-dasharray="{length:.5f} {circumference:.5f}" stroke-dashoffset="{-offset:.5f}" transform="rotate(-90 182 {cy})"/>')
        y = cy - (len(entries) - 1) * 18.5 + index * 37
        svg.extend([f'<circle cx="366" cy="{y - 5}" r="5" fill="{color}"/>',
                    f'<text x="384" y="{y}" fill="#DCE7EE" font-size="16">{escape(name)}</text>',
                    f'<text x="745" y="{y}" text-anchor="end" fill="{color}" font-size="16" font-weight="600">{share * 100:.1f}%</text>'])
        offset += length
    svg.extend([f'<text x="182" y="{cy + 1}" text-anchor="middle" fill="#EDF3F7" font-size="32" font-weight="700">{count}</text>',
                f'<text x="182" y="{cy + 24}" text-anchor="middle" fill="#94A6B6" font-size="12">repositórios</text>',
                '</g></svg>'])
    return "\n".join(svg) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path)
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8-sig")) if args.data else collect("DiasJZ")
    output = ROOT / "assets" / "languages.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data), encoding="utf-8")
    print("Updated assets/languages.svg using public repository language bytes.")
