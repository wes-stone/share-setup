"""Quick smoke tests for critical components."""

from copilot_setup.installer.mcp import _strip_jsonc_comments
from copilot_setup.models import Profile
import json
from pathlib import Path


def test_jsonc_preserves_urls():
    test = '{\n  // comment\n  "http.proxy": "http://proxy.example.com:8080",\n  "url": "https://api.example.com/v1"\n}'
    result = json.loads(_strip_jsonc_comments(test))
    assert result["http.proxy"] == "http://proxy.example.com:8080", "URL corrupted"
    assert result["url"] == "https://api.example.com/v1", "URL corrupted"
    print("  PASS: JSONC preserves URLs")


def test_jsonc_removes_comments():
    test = '{\n  // single line\n  "key": "value",\n  /* block\n  comment */\n  "key2": "value2"\n}'
    result = json.loads(_strip_jsonc_comments(test))
    assert result["key"] == "value"
    assert result["key2"] == "value2"
    print("  PASS: JSONC removes comments")


def test_jsonc_trailing_commas():
    test = '{"a": 1, "b": 2,}'
    result = json.loads(_strip_jsonc_comments(test))
    assert result == {"a": 1, "b": 2}
    print("  PASS: JSONC handles trailing commas")


def test_jsonc_strings_with_slashes():
    test = '{"path": "C://Users//test", "note": "no // issue here"}'
    result = json.loads(_strip_jsonc_comments(test))
    assert result["path"] == "C://Users//test"
    assert result["note"] == "no // issue here"
    print("  PASS: JSONC preserves // in strings")


def test_profile_loads():
    p = Profile.from_toml_path(Path("profiles/default/profile.toml"))
    assert p.name == "Engineering Team"
    assert len(p.prerequisites) == 5
    assert len(p.extensions) == 3
    assert len(p.mcp_servers) == 1
    assert len(p.setup_steps) == 2
    assert p.copilot_instructions_file is not None
    print("  PASS: Profile loads correctly")


if __name__ == "__main__":
    print("Running smoke tests...\n")
    test_jsonc_preserves_urls()
    test_jsonc_removes_comments()
    test_jsonc_trailing_commas()
    test_jsonc_strings_with_slashes()
    test_profile_loads()
    print("\nAll tests passed!")
