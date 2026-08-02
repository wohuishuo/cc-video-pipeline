from pathlib import Path
import sys

APP=Path(__file__).resolve().parents[2]/"apps"/"creator-discovery"
sys.path.insert(0,str(APP))

from creator_discovery.contracts import DiscoveryError, ProfileSpec


def test_supported_profile_url_is_classified_without_credentials():
    value=ProfileSpec.from_url("https://v.douyin.com/2C-fPyMT5Y0/",max_items=74,cookie_key="a"*64)
    assert value.platform=="douyin" and value.max_items==74
    assert "cookie" not in value.to_public_dict()


def test_unsupported_or_invalid_limits_are_rejected():
    for url,limit in (("http://youtube.com/@x",3),("https://example.com/x",3),("https://youtube.com/@x",-1)):
        try: ProfileSpec.from_url(url,max_items=limit)
        except DiscoveryError: pass
        else: raise AssertionError((url,limit))
