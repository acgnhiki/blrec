import hashlib
from typing import Any, List, Tuple


def extract_key(url: str) -> str:
    return url.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def make_key(img_key: str, sub_key: str) -> str:
    # fmt: off
    MAPPING = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    ]
    key = (img_key + sub_key).encode()
    return bytes([key[n] for n in MAPPING]).decode()


def encode_value(value: str) -> str:
    chars = []

    for c in value:
        if c in "!'()*":
            continue
        if (c.isascii() and c.isalnum()) or c in "-_.~":
            chars.append(c)
        else:
            for b in c.encode():
                chars.append(f"%{b:02X}")

    return "".join(chars)


def build_query(key: str, ts: int, params: List[Tuple[str, Any]]) -> str:
    params.append(("wts", str(ts)))
    params.sort(key=lambda p: p[0])

    parts = []
    for name, value in params:
        parts.append(f"{name}={encode_value(str(value))}")
    query = "&".join(parts)

    sign = hashlib.md5((query + key).encode()).hexdigest()
    query += f"&w_rid={sign}"

    return query


def test_extract_key() -> None:
    url = "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png"
    key = extract_key(url)
    assert key == "7cd084941338484aae1ad9425b84077c"


def test_make_key() -> None:
    img_key = "7cd084941338484aae1ad9425b84077c"
    sub_key = "4932caff0ff746eab6f01bf08b70ac45"
    expected = "ea1db124af3c7062474693fa704f4ff8"
    key = make_key(img_key, sub_key)
    assert key == expected


def test_encode_value() -> None:
    expected = "-_-%20F%20%E5%93%94~"
    assert encode_value(")-_-( F**' 哔~!") == expected


def test_build_query() -> None:
    img_key = "7cd084941338484aae1ad9425b84077c"
    sub_key = "4932caff0ff746eab6f01bf08b70ac45"

    key = make_key(img_key, sub_key)
    ts = 1748867128
    params = [("foo", ")-_-( F**' 哔~!"), ("bar", 2333)]

    expected = "bar=2333&foo=-_-%20F%20%E5%93%94~&wts=1748867128&w_rid=6ba96e28a3f09b40e704f1e4b4f8e3e3"  # noqa
    assert build_query(key, ts, params) == expected


if __name__ == "__main__":
    test_extract_key()
    test_make_key()
    test_encode_value()
    test_build_query()
