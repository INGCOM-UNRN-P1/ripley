"""Unit tests for socket fault injection via LD_PRELOAD interposer."""

import shutil
import socket as pysocket
import subprocess

import pytest

from ripley.tools.socket_faults import SocketFaultInjector


def _gcc_available() -> bool:
    return shutil.which("gcc") is not None


def _sockets_creatable() -> bool:
    try:
        pysocket.socket(pysocket.AF_INET, pysocket.SOCK_STREAM).close()
        return True
    except OSError:
        return False


def _compile_plain(name: str, body: str, tmp_path) -> "object":
    """Compila sin sanitizadores: el shim requiere interposición limpia."""
    src = tmp_path / name
    src.write_text(body, encoding="utf-8")
    binary = src.with_suffix(".out")
    res = subprocess.run(
        ["gcc", "-std=c11", "-O0", str(src), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    return binary


LEAKY_PROGRAM = """
#include <signal.h>
#include <sys/socket.h>
int main(void) {
    signal(SIGPIPE, SIG_IGN);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return 2;
    send(fd, "x", 1, 0);
    /* Sin close(): descriptor filtrado. */
    return 0;
}
"""

CLEAN_PROGRAM = """
#include <signal.h>
#include <sys/socket.h>
#include <unistd.h>
int main(void) {
    signal(SIGPIPE, SIG_IGN);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return 2;
    send(fd, "x", 1, 0);
    close(fd);
    return 0;
}
"""

NO_SOCKET_PROGRAM = """
#include <stdio.h>
int main(void) { puts("sin sockets"); return 0; }
"""


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
@pytest.mark.skipif(not _sockets_creatable(), reason="No se pueden crear sockets en este entorno")
def test_audit_detects_leaked_socket(tmp_path):
    leaky = _compile_plain("leaky.c", LEAKY_PROGRAM, tmp_path)
    with SocketFaultInjector() as injector:
        audit = injector.audit(leaky)
    assert audit.available
    assert audit.baseline is not None
    assert audit.baseline.sockets_created == 1
    assert audit.baseline.sockets_closed == 0
    assert audit.baseline.leaked_fds == 1
    assert audit.leaks_under_faults


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
@pytest.mark.skipif(not _sockets_creatable(), reason="No se pueden crear sockets en este entorno")
def test_audit_clean_program_without_leaks(tmp_path):
    clean = _compile_plain("clean.c", CLEAN_PROGRAM, tmp_path)
    with SocketFaultInjector() as injector:
        audit = injector.audit(clean)
    assert audit.available
    assert audit.baseline.leaked_fds == 0
    assert not audit.leaks_under_faults


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_program_without_sockets_short_circuits(tmp_path):
    plain = _compile_plain("plain.c", NO_SOCKET_PROGRAM, tmp_path)
    with SocketFaultInjector() as injector:
        audit = injector.audit(plain)
    assert audit.available
    assert not audit.baseline.uses_sockets
    assert "no crea sockets" in audit.message


@pytest.mark.skipif(not _gcc_available(), reason="gcc no disponible")
def test_missing_binary_reported():
    with SocketFaultInjector() as injector:
        audit = injector.audit("/no/existe/xyz.out")
    assert not audit.available
