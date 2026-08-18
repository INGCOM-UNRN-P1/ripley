"""Unit tests for preventive C security scanner."""

from ripley.config import SecurityConfig
from ripley.security import SecurityScanner, strip_c_comments_and_strings


def test_strip_c_comments_and_strings():
    code = """
    // system("rm -rf /");
    /* #include <unistd.h>
       fork(); */
    char *s = "fork() inside string";
    int x = 10;
    """
    clean = strip_c_comments_and_strings(code)
    assert "system" not in clean
    assert "unistd.h" not in clean
    assert "fork" not in clean
    assert "int x = 10;" in clean


def test_security_scanner_detects_forbidden_calls():
    cfg = SecurityConfig(forbidden_calls=["system", "fork", "popen"], forbidden_headers=["unistd.h"])
    scanner = SecurityScanner(cfg)

    c_code = """
    #include <stdio.h>
    #include <unistd.h>

    int main() {
        system("echo hello");
        fork();
        return 0;
    }
    """
    violations = scanner.scan_code("malicious.c", c_code)
    symbols = [v.symbol for v in violations]

    assert "unistd.h" in symbols
    assert "system" in symbols
    assert "fork" in symbols
    assert len(violations) == 3


def test_security_scanner_ignores_clean_code():
    cfg = SecurityConfig(forbidden_calls=["system", "fork"], forbidden_headers=["unistd.h"])
    scanner = SecurityScanner(cfg)

    c_code = """
    #include <stdio.h>
    #include <stdlib.h>

    int main() {
        printf("Clean program\\n");
        return 0;
    }
    """
    violations = scanner.scan_code("clean.c", c_code)
    assert len(violations) == 0
