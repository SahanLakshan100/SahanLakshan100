"""Builds dark_mode.svg and light_mode.svg: a neofetch-style profile card.
Left: ASCII portrait (ascii.txt). Right: info + live GitHub stats.
Stats are fetched with GITHUB_TOKEN when available (GitHub Actions); otherwise placeholders are shown."""
import os, json, html, urllib.request, urllib.error

USER = "SahanLakshan100"
NAME_LINE = "sahan@lakshan"
CHAR_W, LINE_H, FS = 7.2, 14.5, 12
WIDTH_CH = 56                       # width of the right-hand panel in characters

INFO = [
    ("Role", "Full Stack Developer"),
    ("Host", "Sri Lanka"),
    ("Focus", "Modern web apps, Clean UI"),
    None,
    ("Languages.Programming", "PHP, Python, C#, JavaScript"),
    ("Languages.Web", "HTML, CSS, Bootstrap, Angular"),
    ("Runtime", "Node.js"),
    ("Design", "Figma"),
]
CONTACT = [
    ("Portfolio", "sahanlakshan100.github.io"),
    ("LinkedIn", "sahan-lakshan"),
    ("Instagram", "_sahan_lakshan_"),
    ("GitHub", USER),
]

def _api(url, token, data=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "profile-card"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} on {url}: {e.read().decode()[:300]}")

def fetch_stats_graphql(token):
    q = """query($u:String!){user(login:$u){followers{totalCount} following{totalCount}
      repositories(ownerAffiliation:OWNER, privacy:PUBLIC, first:100){totalCount nodes{stargazerCount}}
      contributionsCollection{totalCommitContributions contributionCalendar{totalContributions}}}}"""
    res = _api("https://api.github.com/graphql", token, json.dumps({"query": q, "variables": {"u": USER}}).encode())
    if res.get("errors"):
        raise RuntimeError(f"GraphQL errors: {res['errors']}")
    u = res["data"]["user"]
    return {
        "Repos": u["repositories"]["totalCount"],
        "Stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "Commits (1y)": u["contributionsCollection"]["totalCommitContributions"],
        "Contributions (1y)": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "Followers": u["followers"]["totalCount"],
        "Following": u["following"]["totalCount"],
    }

def fetch_stats_rest(token):
    u = _api(f"https://api.github.com/users/{USER}", token)
    repos = _api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", token)
    return {
        "Repos": u["public_repos"],
        "Stars": sum(r.get("stargazers_count", 0) for r in repos),
        "Commits (1y)": "--",
        "Contributions (1y)": "--",
        "Followers": u["followers"],
        "Following": u["following"],
    }

def fetch_stats():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("No GITHUB_TOKEN found, using placeholders (this is normal when running locally).")
        return None
    try:
        return fetch_stats_graphql(token)
    except Exception as e:
        print("GraphQL failed, falling back to REST:", e)
        return fetch_stats_rest(token)

def build(theme, stats):
    pal = {
        "dark":  dict(bg="#0d1117", border="#30363d", ascii="#58c8e6", key="#ffa657", val="#79c0ff", dim="#6e7681", head="#00b4d8"),
        "light": dict(bg="#ffffff", border="#d0d7de", ascii="#0a7ea4", key="#bc4c00", val="#0550ae", dim="#8c959f", head="#0a7ea4"),
    }[theme]
    meta = json.load(open("portrait_meta.json"))
    portrait = open(f"portrait_{theme}.txt").read()
    pad = 28
    ax = pad
    px = ax + int(meta["cols"] * meta["cw"]) + 40
    n_art_rows = meta["rows"]
    height = int(n_art_rows * meta["lh"] + pad * 2)
    width = int(px + WIDTH_CH * CHAR_W + pad)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           f'<style>text{{font-family:ui-monospace,SFMono-Regular,Consolas,"DejaVu Sans Mono","Courier New",monospace;font-size:{FS}px;white-space:pre}}'
           f'.k{{fill:{pal["key"]}}}.v{{fill:{pal["val"]}}}.d{{fill:{pal["dim"]}}}.h{{fill:{pal["head"]};font-weight:bold}}.p{{font-size:{meta["fs"]}px}}</style>',
           f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="12" fill="{pal["bg"]}" stroke="{pal["border"]}"/>']

    # ASCII portrait (colored runs, absolutely positioned so alignment never depends on the font)
    out.append(f'<g transform="translate({ax},{pad})"><text class="p" xml:space="preserve">')
    out.append(portrait)
    out.append('</text></g>')

    # right panel
    rows = []                     # list of (kind, parts)
    def rule(title):
        n = WIDTH_CH - len(title) - 3
        return ("rule", f"- {title} " + "\u2014" * max(n, 3))
    def kv(k, v):
        label = f". {k}:"
        dots = WIDTH_CH - len(label) - len(str(v)) - 2
        return ("kv", (label, " " + "." * max(dots, 2) + " ", str(v)))
    rows.append(("head", NAME_LINE + " " + "\u2014" * (WIDTH_CH - len(NAME_LINE) - 1)))
    for item in INFO:
        rows.append(("blank", "") if item is None else kv(*item))
    rows.append(("blank", ""))
    rows.append(rule("Contact"))
    for k, v in CONTACT: rows.append(kv(k, v))
    rows.append(("blank", ""))
    rows.append(rule("GitHub Stats"))
    s = stats or {k: "--" for k in ["Repos", "Stars", "Commits (1y)", "Contributions (1y)", "Followers", "Following"]}
    for k, v in s.items(): rows.append(kv(k, v))

    top = pad + 10 + max(0, (n_art_rows * meta['lh'] - len(rows) * LINE_H) / 2)
    out.append('<text xml:space="preserve">')
    for i, (kind, p) in enumerate(rows):
        y = f"{top + i*LINE_H:.1f}"
        if kind == "head":   out.append(f'<tspan class="h" x="{px}" y="{y}">{html.escape(p)}</tspan>')
        elif kind == "rule": out.append(f'<tspan class="h" x="{px}" y="{y}">{html.escape(p)}</tspan>')
        elif kind == "kv":
            a, b, c = p
            out.append(f'<tspan x="{px}" y="{y}"><tspan class="k">{html.escape(a)}</tspan><tspan class="d">{html.escape(b)}</tspan><tspan class="v">{html.escape(c)}</tspan></tspan>')
    out.append('</text></svg>')
    return "\n".join(out)

if __name__ == "__main__":
    try:
        stats = fetch_stats()
    except Exception as e:                      # never break the workflow because of a stats hiccup
        print("stats unavailable:", e); stats = None
    for theme in ("dark", "light"):
        open(f"{theme}_mode.svg", "w").write(build(theme, stats))
    print("built", "with live stats" if stats else "with placeholder stats")
