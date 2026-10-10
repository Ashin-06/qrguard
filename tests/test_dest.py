import pytest

from qrguard import dest

EXP = {"domains": ["parkmobile.io"]}


def sigs(payload, expect=None):
    return {f["signal"]: f["severity"] for f in dest.analyse(payload, expect)["findings"]}


@pytest.mark.parametrize("url,signal", [
    ("https://parkmobile.io/zone/1234", "expected_domain"),
    ("https://pay.parkmobile.io/zone/1234", "expected_domain"),
    ("https://parkmobi1e.io/zone/1234", "lookalike_domain"),        # 1 for l
    ("https://parkrnobile.io/zone", "lookalike_domain"),             # rn for m
    ("https://parkmoblie.io/zone", "lookalike_domain"),              # transposition
    ("https://park-mobile.io/", "lookalike_domain"),                 # inserted hyphen
    ("https://parkmobile.io.pay-now.com/zone", "brand_in_subdomain"),
    ("https://totally-unrelated.net/pay", "unexpected_domain"),
])
def test_url_domain_checks(url, signal):
    s = sigs(url, EXP)
    assert signal in s
    assert dest.analyse(url, EXP)["risk"] == ("low" if signal == "expected_domain" else "high")


def test_url_tricks_without_expectation():
    assert sigs("http://example.com")["not_https"] == "medium"
    assert sigs("https://203.0.113.9/pay")["ip_address_host"] == "high"
    assert sigs("https://[2001:db8::1]/pay")["ip_address_host"] == "high"
    u = dest.analyse("https://parkmobile.io@evil.example/pay")
    assert u["risk"] == "high" and "parkmobile.io" in u["findings"][0]["detail"]
    assert sigs("https://bit.ly/3abcd")["redirect_service"] == "medium"
    assert sigs("https://a.b.c.d.example.com/")["deep_subdomain"] == "low"
    assert dest.analyse("https://example.com/")["risk"] == "low"


def test_punycode_lookalike():
    host = "аpple.com".encode("idna").decode()  # Cyrillic a
    assert host.startswith("xn--")
    s = dest.analyse(f"https://{host}/login", {"domains": ["apple.com"]})
    assert s["risk"] == "high"
    f = next(x for x in s["findings"] if x["signal"] == "internationalised_domain")
    assert "аpple.com" in f["detail"]


def test_registrable_and_distance():
    assert dest.registrable("shop.example.co.uk") == "example.co.uk"
    assert dest.registrable("a.b.example.com") == "example.com"
    assert dest.osa_distance("parkmobile", "parkmoblie") == 1
    assert dest.osa_distance("abc", "abc") == 0 and dest.osa_distance("", "ab") == 2


def test_upi_checks():
    good = "upi://pay?pa=sharma.store@okaxis&pn=Sharma%20Store&mc=5411"
    assert dest.analyse(good, {"vpa": "sharma.store@okaxis", "name": "Sharma Store"})["risk"] == "low"
    bad = dest.analyse("upi://pay?pa=9876543210@ybl&pn=Sharma%20Store", {"vpa": "sharma.store@okaxis"})
    assert bad["risk"] == "high" and any(f["signal"] == "upi_payee_mismatch" for f in bad["findings"])
    assert sigs("upi://pay?pa=x@okaxis&pn=Other Name", {"vpa": "x@okaxis", "name": "Sharma Store"})[
        "upi_name_mismatch"] == "medium"
    assert sigs("upi://pay?pa=x@okaxis&am=4999")["upi_amount_prefilled"] == "medium"
    assert sigs("upi://pay?pn=NoPayee")["upi_no_payee"] == "high"
    assert sigs("upi://pay?pa=not a vpa")["upi_bad_vpa"] == "high"
    assert sigs("UPI://PAY?PA=Sharma.Store@OKAXIS", {"vpa": "sharma.store@okaxis"})["upi_expected_payee"] == "info"


def test_registered_payload_and_types():
    reg = "upi://pay?pa=sharma.store@okaxis&pn=Sharma%20Store"
    assert sigs(reg, {"payload": reg})["registered_payload"] == "info"
    assert sigs(reg + "x", {"payload": reg})["registered_payload"] == "high"
    assert dest.classify("WIFI:S:cafe;T:WPA;P:pw;;") == "other_scheme"
    assert dest.classify("hello") == "text"
    assert sigs("hello", {"domains": ["parkmobile.io"]})["unexpected_type"] == "high"
    assert dest.analyse("https://", EXP)["risk"] == "high"


def test_trailing_dot_host_is_the_same_domain():
    r = dest.analyse("https://parkmobile.io./zone/1", EXP)
    assert r["risk"] == "low" and "expected_domain" in {f["signal"] for f in r["findings"]}
