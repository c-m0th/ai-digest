"""摘要前的确定性去重；不调用模型、不请求外部服务。"""
import hashlib
import html
import re
import unicodedata
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid",
                 "_ga", "_gl", "igshid", "mkt_tok"}
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s<>\"?#]+", re.I)
ARXIV_PATTERN = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})(?:v\d+)?", re.I)


def canonical_url(value):
    """只删除明确的跟踪参数；保留可能决定文章身份的其他查询参数。"""
    value = html.unescape(str(value or "")).strip()
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        host = parsed.hostname.lower()
        if host.startswith("www."):
            host = host[4:]
        port = parsed.port
        if port and not (parsed.scheme.lower() == "http" and port == 80
                         or parsed.scheme.lower() == "https" and port == 443):
            host += f":{port}"
        query = sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                       if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS)
        path = re.sub(r"%[0-9a-fA-F]{2}", lambda m: m[0].upper(), parsed.path.rstrip("/"))
        return urlunsplit(("https", host, path, urlencode(query), ""))
    except (ValueError, TypeError):
        return ""


def normalized_title(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = unicodedata.normalize("NFKC", value).casefold()
    value = " ".join("".join(ch if ch.isalnum() else " " for ch in value).split())
    cjk = len(re.findall(r"[\u3400-\u9fff]", value))
    if (len(value) >= 24 and len(value.split()) >= 4) or cjk >= 12:
        return value
    return ""  # Editorial、Correction 等短标题不能单独决定身份。


def fingerprints(item):
    keys = set()
    url = canonical_url(item.get("url", ""))
    if url:
        keys.add("url:" + url)
    title = normalized_title(item.get("title", ""))
    if title:
        keys.add("title:" + hashlib.sha256(title.encode("utf-8")).hexdigest())
    # 不扫描摘要里的参考文献 DOI，只读取本条目的 URL/标识字段。
    doi_values = [item.get("doi", ""), item.get("dc_identifier", ""), item.get("prism_doi", "")]
    if url:
        parsed = urlsplit(url)
        doi_values.append(unquote(parsed.path))
        doi_values.extend(v for k, v in parse_qsl(parsed.query) if k.lower() == "doi")
        path = unquote(parsed.path)
        host = parsed.hostname or ""
        if host in {"arxiv.org", "export.arxiv.org"}:
            match = re.fullmatch(r"/(?:abs|pdf|html)/(.+?)(?:\.pdf)?", path)
            if match and ARXIV_PATTERN.fullmatch(match[1]):
                keys.add("arxiv:" + re.sub(r"v\d+$", "", match[1], flags=re.I).lower())
        if host == "pubmed.ncbi.nlm.nih.gov" and re.fullmatch(r"/\d+", path):
            keys.add("pmid:" + path.strip("/"))
        if host == "ncbi.nlm.nih.gov":
            match = re.fullmatch(r"/pubmed/(\d+)", path)
            if match:
                keys.add("pmid:" + match[1])
    for value in doi_values:
        if isinstance(value, str):
            match = DOI_PATTERN.search(unquote(html.unescape(value)))
            if match:
                keys.add("doi:" + match[0].rstrip(".,;").lower())
    arxiv_id = str(item.get("arxiv_id", "")).strip()
    if ARXIV_PATTERN.fullmatch(arxiv_id):
        keys.add("arxiv:" + re.sub(r"v\d+$", "", arxiv_id, flags=re.I).lower())
    pmid = str(item.get("pmid", "")).strip()
    if pmid.isdigit():
        keys.add("pmid:" + pmid)
    return keys


def deduplicate_items(items, recent_keys=()):
    """合并当天跨来源别名，再与近期已投递身份比较；每组保留内容最长的一条。"""
    recent_keys = set(recent_keys)
    keys = [fingerprints(item) for item in items]
    parents = list(range(len(items)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    owners = {}
    for i, item_keys in enumerate(keys):
        for key in item_keys:
            if key in owners:
                a, b = root(i), root(owners[key])
                if a != b:
                    parents[a] = b
            else:
                owners[key] = i
    groups = {}
    for i in range(len(items)):
        groups.setdefault(root(i), []).append(i)
    result = []
    history_count = 0
    for group in groups.values():
        all_keys = set().union(*(keys[i] for i in group))
        if all_keys & recent_keys:
            history_count += 1
            continue
        best = max(group, key=lambda i: len(str(items[i].get("content") or "")))
        item = dict(items[best])
        item["_dedup_keys"] = sorted(all_keys)
        result.append(item)
    stats = {"input": len(items), "same_batch": len(items) - len(groups),
             "recent": history_count, "kept": len(result)}
    return result, stats
