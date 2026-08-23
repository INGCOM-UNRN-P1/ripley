"""Heap memory fragmentation simulator and dynamic memory allocation analyzer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class HeapBlock:
    offset: int
    size: int
    is_free: bool = True
    tag: str = ""


@dataclass
class HeapSimulationReport:
    total_capacity: int
    peak_allocated: int
    current_allocated: int
    total_free: int
    largest_free_block: int
    fragmentation_index: float  # 0.0 (sin fragmentación) a 1.0 (fragmentación total)
    blocks: List[HeapBlock]
    memory_map: str


class HeapMemorySimulator:
    """Simula un montículo (Heap) de memoria para analizar patrones de fragmentación externa e interna."""

    def __init__(self, capacity: int = 1024) -> None:
        self.capacity = capacity
        self.blocks: List[HeapBlock] = [HeapBlock(offset=0, size=capacity, is_free=True, tag="free")]
        self.peak_allocated = 0

    def allocate(self, size: int, tag: str = "alloc") -> Optional[int]:
        """Asigna un bloque de memoria usando la estrategia First-Fit."""
        if size <= 0:
            return None

        # Alinear a múltiplos de 4 bytes
        aligned_size = (size + 3) & ~3

        for idx, block in enumerate(self.blocks):
            if block.is_free and block.size >= aligned_size:
                allocated_offset = block.offset
                remaining_size = block.size - aligned_size

                # Reemplazar bloque libre por el asignado
                self.blocks[idx] = HeapBlock(
                    offset=allocated_offset,
                    size=aligned_size,
                    is_free=False,
                    tag=tag,
                )

                # Si sobró espacio, insertar un nuevo bloque libre
                if remaining_size > 0:
                    self.blocks.insert(
                        idx + 1,
                        HeapBlock(
                            offset=allocated_offset + aligned_size,
                            size=remaining_size,
                            is_free=True,
                            tag="free",
                        ),
                    )

                curr_alloc = sum(b.size for b in self.blocks if not b.is_free)
                if curr_alloc > self.peak_allocated:
                    self.peak_allocated = curr_alloc

                return allocated_offset

        return None  # No hay espacio contiguo suficiente (falla por fragmentación o falta de memoria)

    def free(self, offset: int) -> bool:
        """Libera un bloque previamente asignado y compacta bloques libres contiguos."""
        found_idx = -1
        for idx, block in enumerate(self.blocks):
            if block.offset == offset and not block.is_free:
                found_idx = idx
                break

        if found_idx == -1:
            return False

        self.blocks[found_idx].is_free = True
        self.blocks[found_idx].tag = "free"

        # Coalescencia / Compactación de bloques libres contiguos
        merged_blocks: List[HeapBlock] = []
        for b in self.blocks:
            if merged_blocks and merged_blocks[-1].is_free and b.is_free:
                merged_blocks[-1].size += b.size
            else:
                merged_blocks.append(b)

        self.blocks = merged_blocks
        return True

    def calculate_fragmentation(self) -> Tuple[int, int, float]:
        """Calcula memoria libre total, bloque libre más grande y el índice de fragmentación."""
        total_free = sum(b.size for b in self.blocks if b.is_free)
        largest_free = max((b.size for b in self.blocks if b.is_free), default=0)

        if total_free == 0:
            frag_index = 0.0
        else:
            # Índice de fragmentación: 1 - (bloque_libre_max / total_libre)
            frag_index = 1.0 - (largest_free / total_free)

        return total_free, largest_free, round(frag_index, 3)

    def generate_memory_map(self, width: int = 40) -> str:
        """Genera una barra visual ASCII del estado del montículo."""
        chars = []
        for b in self.blocks:
            b_width = max(1, int((b.size / self.capacity) * width))
            char = "░" if b.is_free else "█"
            chars.append(char * b_width)

        raw_map = "".join(chars)
        # Ajustar a ancho exacto
        if len(raw_map) > width:
            raw_map = raw_map[:width]
        elif len(raw_map) < width:
            raw_map = raw_map.ljust(width, "░")

        return f"[{raw_map}]"

    def get_report(self) -> HeapSimulationReport:
        total_free, largest_free, frag_index = self.calculate_fragmentation()
        curr_alloc = sum(b.size for b in self.blocks if not b.is_free)

        return HeapSimulationReport(
            total_capacity=self.capacity,
            peak_allocated=self.peak_allocated,
            current_allocated=curr_alloc,
            total_free=total_free,
            largest_free_block=largest_free,
            fragmentation_index=frag_index,
            blocks=list(self.blocks),
            memory_map=self.generate_memory_map(),
        )
