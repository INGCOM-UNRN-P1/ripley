# Plan — Modo Evaluación Presencial con Bloqueo de Red (Exam Lockout Mode)

> Estado: PROPUESTA DE DISEÑO — propuesta #30 del registro (`docs/referencia/docs/referencia/mejoras.md`, Módulo 5).
> Principio rector: **herramienta técnica local, abierta y auditable** para exámenes presenciales
> de programación en C — no un sistema de vigilancia.

---

## 1. Problema y alcance

En exámenes presenciales de Programación I los estudiantes codifican en máquinas de laboratorio o
propias. El docente necesita garantizar, sin infraestructura de videovigilancia ni software
comercial invasivo, que durante la evaluación:

1. No haya acceso a internet (foros, IA en la nube, pastebin, repositorios).
2. No haya comunicación entre estudiantes (chat LAN, carpetas compartidas, AirDrop/SMB).
3. No se consulten soluciones pre-cargadas en la máquina (USB, carpetas sincronizadas, historial).
4. El tiempo sea verificable y las entregas lleguen íntegras y atribuibles.
5. El entorno de compilación sea el declarado (misma filosofía que las instantáneas herméticas).

**Fuera de alcance explícito** (honesto y deliberado):

- Determinado adversario capaz de evadir controles del SO o usar un segundo dispositivo (celular):
  eso es territorio de reglamento de cátedra y supervisión humana, no de esta herramienta.
- Captura de pantalla, cámara, keyloggers o cualquier forma de monitoreo del estudiante.
  **Ripley jamás registrará contenido de pantalla ni teclas.**
- Exámenes remotos/no presenciales: este modo asume aula física con docente presente.

## 2. Modelo de amenazas

| Amenaza | Vector | Capa que lo mitiga | Residual |
|---|---|---|---|
| Consultar IA/web | Navegador, curl, apps | A (bloqueo de red por firewall/namespaces) | Baja |
| Copiarse entre compañeros | SMB/AirDrop/scp LAN | A + C (entrega firmada por máquina) | Baja |
| Soluciones pre-cargadas | Archivos locales, USB | B (workspace limpio + montaje restringido) + política áulica | Media |
| Extender el tiempo | Reloj del sistema | B (timer monotónico + detección de saltos + sellado HMAC) | Baja |
| Falsificar la entrega | Editar archivos post-hoc | C (sobres firmado con clave de sesión) | Baja |
| Manipular el verificador | Modificar ripley/gcc | C (fingerprint de toolchain + hash de ripley embebidos) | Media |
| Dejar la máquina sin red tras fallo | Crash de ripley | A2 (rollback garantizado: reglas etiquetadas + restauración al boot) | — |

## 3. Arquitectura en cuatro capas

```
┌────────────────────────────────────────────────────────────────────┐
│ D. Distribución y recolección sin internet                          │
│    examen.ripkg ──▶ USB/LAN ──▶ ripley-check exam … ──▶ .rexam ──▶  │
│                                     ▲                    │          │
│ ┌───────────────────────────────────┼────────────────────┼───────┐  │
│ │ C. Integridad de la entrega       │                    ▼       │  │
│ │   sobres firmados (HMAC sesión),  │        registro en flujo de  │  │
│ │   bitácora de eventos, snapshot   │        auditoría docente     │  │
│ │   de toolchain                    │                              │  │
│ ├────────────────────────────────────────────────────────────────┤  │
│ │ B. Sesión de examen (ripley-check exam start/status/submit)      │  │
│ │   workspace limpio · temporizador monotónico · bloqueo de        │  │
│ │   sesión única · eventos locales                                 │  │
│ ├────────────────────────────────────────────────────────────────┤  │
│ │ A. Confinamiento                                                 │  │
│ │   A1 privilegiado: nftables con reglas etiquetadas               │  │
│ │   A2 sin privilegios: bubblewrap --unshare-all (ya existe)       │  │
│ └────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Capa A — Bloqueo de red

**A1 (privilegiado, laboratorio):** perfil `nftables` creado al iniciar el examen y destruido al
cerrarlo. Todas las reglas llevan comentario `ripley-exam-<sesion>` para limpieza quirúrgica sin
tocar el firewall existente.

```text
table inet ripley_exam_<id> {
  set permitas { type ipv4_addr; flags interval; }   # opcional: IP del recolector docente
  chain out {
    type filter hook output priority 0; policy accept;
    oifname != "lo" counter drop comment "ripley-exam-<id>"
  }
  chain in  { type filter hook input priority 0; policy accept;
    iifname != "lo" ct state new counter drop comment "ripley-exam-<id>" }
}
```

* Requiere `sudo` con **consentimiento explícito**: antes de aplicar, Ripley muestra las reglas
  exactas (`--dry-run`) y pide confirmación.
* **Rollback garantizado**: `atexit` + handler de señales ejecutan el borrado de la tabla; además,
  la instalación deja una unidad systemd oneshot (`ripley-exam-restore.service`) que limpia tablas
  etiquetadas en el próximo boot si la máquina se corta la luz a mitad de examen. La unidad se
  elimina al cerrar la sesión normalmente.
* Contadores de la tabla alimentan la bitácora: intentos de salida bloqueados → evento `E_NET_BLOCKED`.

**A2 (sin privilegios, notebook personal):** reutiliza `NamespaceSandbox` (bubblewrap
`--unshare-all`, ya implementado en `tools/sandbox.py`). El editor + terminal de compilación corren
dentro del sandbox sin red; nada requiere root. Es el modo por defecto cuando no hay sudo.

**Otros sistemas:** Windows (reglas de Firewall de Defender vía PowerShell con prefijo de nombre de
regla equivalente) y macOS (ancla PF) quedan como perfiles *best-effort* en F5, con el mismo
contrato de limpieza y el mismo modo A2 disponible siempre.

### Capa B — Sesión de examen

`ripley-check exam start <examen.ripkg>`:

1. Verifica firma del bundle (reutiliza verificación GPG/SHA-256 de `pipeline/bundle.py`).
2. Crea workspace limpio `~/ExamenRipley/<actividad>/` (rechaza directorios preexistentes no vacíos).
3. Toma **lock exclusivo** (`exam.lock` con PID): una sola sesión activa por usuario/máquina.
4. Aplica capa A según disponibilidad (`doctor` decide A1/A2/fallo).
5. Registra hora de inicio **doble**: reloj de pared (sellado) y `time.monotonic()` como referencia
   de duración real; si al entregar la brecha pared-monotónico supera un umbral → evento
   `E_CLOCK_JUMP` y marca de sospecha.
6. Opcional `--launch-editor`: abre el editor dentro del mismo sandbox A2.

`exam status` muestra tiempo restante y eventos registrados; `exam submit` cierra sesión, genera el
sobre (capa C) y ejecuta el rollback de red. `exam abort` permite al docente cancelar con registro.

Eventos locales (JSONL append-only, `eventos.jsonl`): `E_START`, `E_SUBMIT`, `E_LATE`,
`E_CLOCK_JUMP`, `E_NET_BLOCKED`, `E_SESSION_CONFLICT`, `E_ABORT`, `E_TOOLCHAIN_MISMATCH`.

### Capa C — Integridad de la entrega

El resultado de `exam submit` es un sobre **`.rexam`** (zip, mismo motor que `.ripkg`):

```toml
[meta]
tipo = "rexam" ; actividad ; alumno (declarat.) ; inicio_utc ; fin_utc ; duracion_seg

[integridad]
sha256 = { … fuentes y eventos … }
hmac = "…HMAC-SHA256(inicio|fin|hash_fuentes, clave_de_sesion)…"

[entorno]
toolchain = { gcc_version, target, libc }   # snapshot capturado al start (ítem 58)
ripley_version = "0.1.0"
sandbox_mode = "bwrap"                      # o "nftables"

[eventos]  # resumen de conteos; detalle completo en eventos.jsonl dentro del zip
net_blocked = 3 ; clock_jumps = 0 ; late = false
```

* `clave_de_sesion` deriva del secreto del bundle de examen (que solo tiene el docente): el
  estudiante **no puede** fabricar ni modificar horarios sin invalidar el HMAC.
* Al recibirlo, el docente verifica HMAC + hashes y consulta eventos: cualquier anomalía puede
  mover la entrega al estado `sospechosa` del flujo de auditoría ya implementado
  (`teacher/audit.py`) — integración directa, cero trabajo extra.

### Capa D — Distribución y recolección

- **Distribución**: `ripley practica pack --exam --duracion 90` genera el bundle de examen
  (consigna + restricciones automáticas vía `core/restrictions.py` + testcases públicos +
  secreto de sesión embebido cifrado para el docente). Se lleva por USB o carpeta compartida
  **antes** de aislar la red.
- **Recolección**: tres caminos equivalentes:
  1. USB al cierre (el sobre está listo en disco).
  2. `ripley-check exam submit --to <ip-docente>` por el único hueco permitido del perfil A1
     (puerto del recolector simple incluido: `ripley exam serve-receiver --out dir/`).
  3. Carpeta de red del laboratorio.
- En recepción: `ripley exam collect dir/` valida cada sobre y registra las entregas directamente
  en el tablero de auditoría (`estado inicial: evaluada`, o `sospechosa` si eventos anómalos).

## 4. Superficie CLI resultante

Estudiante (`ripley-check`):

```bash
ripley-check exam doctor                     # ¿sudo? ¿bwrap? ¿Xvfb? veredicto de modo
ripley-check exam start examen-1.ripkg [--no-net-lock] [--launch-editor]
ripley-check exam status                     # tiempo restante, últimos eventos
ripley-check exam submit [--to ip]           # genera .rexam + rollback de red
ripley-check exam net --dry-run              # mostrar reglas exactas antes de aceptar
```

Docente (`ripley`):

```bash
ripley practica pack entrega-final --exam --duracion 90 --restrictions estricto
ripley exam serve-receiver --port 8899 --out recibidos/
ripley exam collect recibidos/ --actividad entrega-final   # valida + llena tablero audit
```

Config nueva `[exam]` en `ripley.toml`: `enabled=false`, `modo_red="auto|nftables|bwrap|none"`,
`permitir_ip_recolector=""`, `umbral_clock_jump_seg=5`, `tolerancia_late_min=2`.

## 5. Seguridad del propio mecanismo

| Vector contra Ripley | Mitigación |
|---|---|
| Matar ripley a mitad de examen | Sin `submit` válido no hay sobre; la carpeta queda y el docente la colecta manualmente; el evento de conflicto queda si reinició sesión |
| Adelantar el reloj | Duración medida con `monotonic()`; salto detectable comparando ambos relojes → `E_CLOCK_JUMP` + HMAC invalidable |
| Editar `eventos.jsonl` | Hash del archivo dentro del manifiesto firmado con clave que el estudiante desconoce |
| Usar otro editor fuera del sandbox (modo A2) | Política áulica; A1 cubre la parte de red igualmente. Documentado como límite |
| Forzar sudo falso | `--dry-run` obligatorio la primera vez por máquina; log local de aplicación de reglas |

## 6. Fases de implementación

| Fase | Alcance | Criterio de salida |
|---|---|---|
| **E0** | Este documento aprobado; decisión A1/A2 por defecto | OK cátedra |
| **E1** | Bundle de examen (`pack --exam`) + sesión con lock/timer/eventos + `status`/`submit` **sin** capa de red (modo `none`) | Ciclo completo probado en máquina limpia; HMAC verificado |
| **E2** | Confinamiento A2 reutilizando `NamespaceSandbox` (editor opcional dentro del sandbox) | Compilar+editar sin red funciona sin sudo |
| **E3** | Bloqueo A1 nftables con etiquetas, dry-run, rollback triple (atexit/señal/systemd-restore) y contadores → eventos | Máquina recupera red ante kill -9 y reboot; suite de pruebas de red simuladas |
| **E4** | Sobre `.rexam` + `exam serve-receiver` + `exam collect` integrando tablero de auditoría | Recepción de 30 sobres simulados: 100% validados, sospechosos marcados |
| **E5** | Perfiles best-effort Windows/macOS + `exam doctor` + MANUAL sección de examen | Doctor correcto en los 3 SO del CI (donde aplique) |

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Laboratorio heterogéneo (imágenes distintas) | `exam doctor` previo al día del examen; modo A2 siempre disponible |
| Estudiante sin permisos de sudo en su notebook | A2 no requiere root; A1 es opt-in con contraseña |
| Miedo a quedar "sin internet para siempre" | Reglas etiquetadas + rollback triple + comando manual de emergencia documentado en pantalla |
| Rechazo institucional (privacidad) | Sin cámaras ni teclado/pantalla: solo metadatos técnicos; documento apto para reglamento |
| Sobres perdidos por falla de USB | Triple canal de recolección; la carpeta local conserva el original hasta confirmación del docente |

## 8. Criterios de aceptación globales

- `exam doctor` nunca miente: si dice "bloqueo activo", `curl ejemplos.com` desde la sesión falla.
- Tras cualquier terminación —incluido kill -9 y corte de energía— la máquina recupera su red
  sin intervención manual (verificado por test automatizado de E3).
- Todo sobre `.rexam` rechazado por HMAC o hash genera estado `sospechosa` + evento visible en
  `ripley audit history`.
- Cero dependencias nuevas de paquetes: todo con stdlib + herramientas ya sondeadas
  (nftables/bwrap opcionales con degradación reportada).

---

*Documento vivo: actualizar estados ✅ por fase a medida que se implemente.*
