"""Network/socket fault injection via a generated LD_PRELOAD interposer.

Compila un shim en C que intercepta socket()/connect()/send()/recv()/close()
para simular conexiones caídas y verificar si el código del alumno cierra
adecuadamente los descriptores ante fallas de red."""

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional


_SOCKET_SHIM_C = r"""
/* Ripley Socket Fault Injection Shim - generado automaticamente */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define RIPLEY_MAX_FD 4096

static int g_fail_after = 0; /* 0 = injection desactivada */
static int g_ops = 0;
static int g_failed_ops = 0;
static int g_created = 0;
static int g_closed = 0;
static unsigned char g_is_socket[RIPLEY_MAX_FD];

__attribute__((constructor)) static void ripley_shim_init(void) {
    const char *fa = getenv("RIPLEY_FAIL_AFTER");
    if (fa) g_fail_after = atoi(fa);
    memset(g_is_socket, 0, sizeof(g_is_socket));
}

__attribute__((destructor)) static void ripley_shim_fini(void) {
    fprintf(stderr,
            "[ripley-socket-shim] creados=%d cerrados=%d fugas=%d fallas_inyectadas=%d\n",
            g_created, g_closed, g_created - g_closed, g_failed_ops);
    fflush(stderr);
}

static int ripley_should_fail(void) {
    if (g_fail_after <= 0) return 0;
    g_ops++;
    if (g_ops >= g_fail_after) {
        g_failed_ops++;
        errno = ECONNRESET;
        return 1;
    }
    return 0;
}

int socket(int domain, int type, int protocol) {
    static int (*real_fn)(int, int, int) = NULL;
    if (!real_fn) real_fn = dlsym(RTLD_NEXT, "socket");
    int fd = real_fn(domain, type, protocol);
    if (fd >= 0 && fd < RIPLEY_MAX_FD) {
        g_is_socket[fd] = 1;
        g_created++;
    }
    return fd;
}

int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen) {
    static int (*real_fn)(int, struct sockaddr *, socklen_t *) = NULL;
    if (!real_fn) real_fn = dlsym(RTLD_NEXT, "accept");
    int fd = real_fn(sockfd, addr, addrlen);
    if (fd >= 0 && fd < RIPLEY_MAX_FD) {
        g_is_socket[fd] = 1;
        g_created++;
    }
    return fd;
}

int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen) {
    static int (*real_fn)(int, const struct sockaddr *, socklen_t) = NULL;
    if (!real_fn) real_fn = dlsym(RTLD_NEXT, "connect");
    if (ripley_should_fail()) return -1;
    return real_fn(sockfd, addr, addrlen);
}

ssize_t send(int sockfd, const void *buf, size_t len, int flags) {
    static ssize_t (*real_fn)(int, const void *, size_t, int) = NULL;
    if (!real_fn) real_fn = dlsym(RTLD_NEXT, "send");
    if (ripley_should_fail()) return -1;
    return real_fn(sockfd, buf, len, flags);
}

ssize_t recv(int sockfd, void *buf, size_t len, int flags) {
    static ssize_t (*real_fn)(int, void *, size_t, int) = NULL;
    if (!real_fn) real_fn = dlsym(RTLD_NEXT, "recv");
    if (ripley_should_fail()) return -1;
    return real_fn(sockfd, buf, len, flags);
}

int close(int fd) {
    static int (*real_fn)(int) = NULL;
    if (!real_fn) real_fn = dlsym(RTLD_NEXT, "close");
    if (fd >= 0 && fd < RIPLEY_MAX_FD && g_is_socket[fd]) {
        g_closed++;
        g_is_socket[fd] = 0;
    }
    return real_fn(fd);
}
"""

_SHIM_SUMMARY_REGEX = re.compile(
    r"\[ripley-socket-shim\] creados=(?P<created>\d+) cerrados=(?P<closed>\d+) "
    r"fugas=(?P<leaked>\d+) fallas_inyectadas=(?P<failed>\d+)"
)


@dataclass
class SocketFaultReport:
    fail_after: int
    exit_code: int
    sockets_created: int = 0
    sockets_closed: int = 0
    leaked_fds: int = 0
    injected_failures: int = 0
    raw_stderr: str = ""

    @property
    def uses_sockets(self) -> bool:
        return self.sockets_created > 0


@dataclass
class SocketFaultAuditResult:
    available: bool
    baseline: Optional[SocketFaultReport] = None
    fault_rounds: List[SocketFaultReport] = field(default_factory=list)
    leaks_under_faults: bool = False
    message: str = ""


class SocketFaultInjector:
    """Inyecta fallas de red en el binario del alumno mediante LD_PRELOAD y
    audita si los descriptores de socket quedan abiertos (*leaked fds*)."""

    def __init__(self, compiler_executable: str = "gcc", timeout_sec: float = 10.0) -> None:
        self.compiler_executable = compiler_executable
        self.timeout_sec = timeout_sec
        self._shim_path: Optional[Path] = None
        self._workdir: Optional[tempfile.TemporaryDirectory] = None

    # ------------------------------------------------------------------
    # Ciclo de vida del shim compilado
    # ------------------------------------------------------------------
    def _ensure_shim(self) -> Optional[Path]:
        if self._shim_path is not None and self._shim_path.exists():
            return self._shim_path
        gcc_bin = shutil.which(self.compiler_executable)
        if not gcc_bin:
            return None
        self._workdir = tempfile.TemporaryDirectory(prefix="ripley_sockshim_")
        work_path = Path(self._workdir.name)
        shim_c = work_path / "ripley_socket_shim.c"
        shim_so = work_path / "ripley_socket_shim.so"
        shim_c.write_text(_SOCKET_SHIM_C, encoding="utf-8")
        try:
            proc = subprocess.run(
                [gcc_bin, "-shared", "-fPIC", "-O1", "-ldl", str(shim_c), "-o", str(shim_so)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            self._cleanup()
            return None
        if proc.returncode != 0 or not shim_so.exists():
            self._cleanup()
            return None
        self._shim_path = shim_so
        return self._shim_path

    def _cleanup(self) -> None:
        if self._workdir is not None:
            self._workdir.cleanup()
        self._workdir = None
        self._shim_path = None

    def __enter__(self) -> "SocketFaultInjector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        self._cleanup()

    # ------------------------------------------------------------------
    # Ejecución con inyección
    # ------------------------------------------------------------------
    def _run_once(self, binary: Path, stdin_data: str, fail_after: int) -> SocketFaultReport:
        shim = self._ensure_shim()
        if shim is None:
            return SocketFaultReport(fail_after=fail_after, exit_code=-1)
        env = dict(os.environ)
        env["LD_PRELOAD"] = str(shim)
        env["RIPLEY_FAIL_AFTER"] = str(fail_after)
        try:
            proc = subprocess.run(
                [str(binary)],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                env=env,
            )
            stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            stdout, stderr, rc = "", "[ripley] timeout durante la ejecución con inyección.", -1
        except OSError as e:
            stdout, stderr, rc = "", f"[ripley] error ejecutando: {e}", -1

        m = _SHIM_SUMMARY_REGEX.search(stderr)
        if m:
            return SocketFaultReport(
                fail_after=fail_after,
                exit_code=rc,
                sockets_created=int(m.group("created")),
                sockets_closed=int(m.group("closed")),
                leaked_fds=int(m.group("leaked")),
                injected_failures=int(m.group("failed")),
                raw_stderr=stderr[-800:],
            )
        return SocketFaultReport(fail_after=fail_after, exit_code=rc, raw_stderr=stderr[-800:])

    def audit(
        self,
        binary_path: Path | str,
        stdin_data: str = "",
        max_fault_rounds: int = 5,
    ) -> SocketFaultAuditResult:
        """Ejecuta una línea base sin fallas y rondas con la N-ésima operación
        de red fallando; detecta fugas de descriptores bajo condiciones adversas."""
        bin_path = Path(binary_path)
        if not bin_path.exists():
            return SocketFaultAuditResult(available=False, message="Binario no encontrado.")
        if self._ensure_shim() is None:
            return SocketFaultAuditResult(available=False, message="No se pudo compilar el shim de inyección.")

        baseline = self._run_once(bin_path, stdin_data, fail_after=0)
        if not baseline.uses_sockets:
            return SocketFaultAuditResult(
                available=True,
                baseline=baseline,
                message="El programa no crea sockets: nada que auditar.",
            )

        rounds: List[SocketFaultReport] = []
        leaks_under_faults = False
        max_ops_hint = max(baseline.sockets_created * 4, 4)
        step = max(1, max_ops_hint // max(max_fault_rounds, 1))
        for fail_at in range(step, max_ops_hint + 1, step)[:max_fault_rounds]:
            rep = self._run_once(bin_path, stdin_data, fail_after=fail_at)
            rounds.append(rep)
            # Fuga real bajo fallas: con inyecciones activas quedaron descriptores
            # abiertos (también delata al programa que nunca cierra, aunque su
            # línea base ya filtrara).
            if rep.injected_failures > 0 and rep.sockets_created > 0 and rep.leaked_fds > 0:
                leaks_under_faults = True

        return SocketFaultAuditResult(
            available=True,
            baseline=baseline,
            fault_rounds=rounds,
            leaks_under_faults=leaks_under_faults,
            message=(
                f"Fugas de descriptores detectadas al fallar operaciones de red ({baseline.leaked_fds} base)."
                if leaks_under_faults
                else "Sin fugas adicionales bajo fallas de red inyectadas."
            ),
        )
