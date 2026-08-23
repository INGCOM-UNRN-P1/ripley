"""Shared CLI plumbing used by both the teacher and the student apps."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()
