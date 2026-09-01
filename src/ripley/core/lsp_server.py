"""Servidor Language Server Protocol (LSP) liviano para diagnósticos 0xXXXXh de Ripley."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ripley.core.engine import analyze_target, run_ast_linters


def diagnostico_to_lsp(diag: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte un hallazgo de Ripley en un objeto Diagnostic de LSP."""
    line = max(0, int(diag.get("linea", diag.get("line", 1))) - 1)
    col = max(0, int(diag.get("columna", diag.get("column", 1))) - 1)
    severidad_raw = str(diag.get("severidad", diag.get("severity", "warning"))).lower()
    
    # LSP DiagnosticSeverity: 1=Error, 2=Warning, 3=Information, 4=Hint
    severity = 1 if severidad_raw in ("error", "fatal", "bloqueante") else 2
    code = str(diag.get("codigo") or diag.get("rule_code") or diag.get("rule_id", "0x0000h"))
    mensaje = str(diag.get("mensaje") or diag.get("message", ""))
    sugerencia = str(diag.get("sugerencia") or diag.get("suggestion", ""))

    msg_formatted = f"[{code}] {mensaje}"
    if sugerencia:
        msg_formatted += f" — {sugerencia}"

    return {
        "range": {
            "start": {"line": line, "character": col},
            "end": {"line": line, "character": col + 10},
        },
        "severity": severity,
        "code": code,
        "source": "Ripley Linter",
        "message": msg_formatted.strip(),
    }


def procesar_lsp_mensaje(mensaje: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Procesa un mensaje JSON-RPC del cliente LSP."""
    method = mensaje.get("method")
    msg_id = mensaje.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "capabilities": {
                    "textDocumentSync": 1,  # Full sync
                    "diagnosticProvider": {"interFileDependencies": False, "workspaceDiagnostics": False},
                },
                "serverInfo": {"name": "ripley-lsp", "version": "2.0.0"},
            },
        }

    elif method in ("textDocument/didSave", "textDocument/didOpen", "textDocument/didChange"):
        params = mensaje.get("params", {})
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        # Extraer ruta local desde URI file://
        if uri.startswith("file://"):
            ruta = Path(uri[7:])
        else:
            ruta = Path(uri)

        diagnostics: List[Dict[str, Any]] = []
        if ruta.is_file() and ruta.suffix in (".c", ".h"):
            try:
                findings = run_ast_linters([ruta])
                for d in findings:
                    diagnostics.append(diagnostico_to_lsp(d))
            except Exception:
                pass

        # Notificación publishDiagnostics
        return {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": uri, "diagnostics": diagnostics},
        }

    elif msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "result": None}

    return None


def run_lsp_server_stdio():
    """Bucle principal de servidor LSP en stdio."""
    while True:
        linea = sys.stdin.readline()
        if not linea:
            break
        if linea.startswith("Content-Length:"):
            try:
                length = int(linea.split(":")[1].strip())
                sys.stdin.readline()  # Leer \r\n vacío
                body = sys.stdin.read(length)
                req = json.loads(body)
                resp = procesar_lsp_mensaje(req)
                if resp:
                    resp_json = json.dumps(resp)
                    sys.stdout.write(f"Content-Length: {len(resp_json.encode('utf-8'))}\r\n\r\n{resp_json}")
                    sys.stdout.flush()
            except Exception:
                pass
