#!/usr/bin/env python3
"""Generate compact, dependency-free PNG thumbnails for ARC task JSON files."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ARC_COLORS = (
    (0x00, 0x00, 0x00),
    (0x00, 0x74, 0xD9),
    (0xFF, 0x41, 0x36),
    (0x2E, 0xCC, 0x40),
    (0xFF, 0xDC, 0x00),
    (0xAA, 0xAA, 0xAA),
    (0xF0, 0x12, 0xBE),
    (0xFF, 0x85, 0x1B),
    (0x7F, 0xDB, 0xFF),
    (0x87, 0x0C, 0x25),
)

WHITE = (0xFF, 0xFF, 0xFF)
TEST_BACKGROUND = (0xE3, 0xE6, 0xEA)
PAGE_BACKGROUND = (0xF3, 0xF4, 0xF6)
INK = (0x25, 0x29, 0x30)
GRID_LINE = (0x66, 0x6B, 0x73)

OUTER_PADDING = 24
SECTION_PADDING = 18
SECTION_GAP = 16
PAIR_GAP = 18
LABEL_HEIGHT = 26
ARROW_HEIGHT = 28
MAX_CELL_SIZE = 12
MIN_CELL_SIZE = 4

# A deliberately tiny font keeps the generator self-contained and deterministic.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
}


Grid = list[list[int]]


@dataclass(frozen=True)
class Pair:
    input: Grid
    output: Grid

    def width(self, cell_size: int) -> int:
        return max(grid_width(self.input, cell_size), grid_width(self.output, cell_size))


class Canvas:
    def __init__(self, width: int, height: int, color: tuple[int, int, int]) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(color * (width * height))

    def rectangle(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        if width <= 0 or height <= 0:
            return
        row = bytes(color) * width
        for py in range(max(0, y), min(self.height, y + height)):
            start = (py * self.width + max(0, x)) * 3
            clipped_width = min(self.width, x + width) - max(0, x)
            self.pixels[start : start + clipped_width * 3] = row[: clipped_width * 3]

    def text(self, x: int, y: int, value: str, scale: int = 2) -> None:
        cursor = x
        for character in value:
            glyph = FONT[character]
            for row_index, row in enumerate(glyph):
                for column_index, pixel in enumerate(row):
                    if pixel == "1":
                        self.rectangle(
                            cursor + column_index * scale,
                            y + row_index * scale,
                            scale,
                            scale,
                            INK,
                        )
            cursor += 6 * scale

    def png_bytes(self) -> bytes:
        scanlines = bytearray()
        row_size = self.width * 3
        for y in range(self.height):
            scanlines.append(0)
            start = y * row_size
            scanlines.extend(self.pixels[start : start + row_size])

        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(
            b"IDAT", zlib.compress(bytes(scanlines), level=9)
        ) + chunk(b"IEND", b"")


def validate_grid(grid: object, context: str) -> Grid:
    if not isinstance(grid, list) or not grid or not all(isinstance(row, list) and row for row in grid):
        raise ValueError(f"{context} must be a non-empty rectangular grid")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError(f"{context} must be rectangular")
    if any(not isinstance(value, int) or not 0 <= value < len(ARC_COLORS) for row in grid for value in row):
        raise ValueError(f"{context} contains a value outside the ARC palette (0-9)")
    return grid


def load_pairs(task_path: Path, split: str) -> list[Pair]:
    task = json.loads(task_path.read_text())
    examples = task.get(split)
    if not isinstance(examples, list) or not examples:
        raise ValueError(f"{task_path}: missing non-empty '{split}' list")
    pairs = []
    for index, example in enumerate(examples):
        if not isinstance(example, dict) or "input" not in example or "output" not in example:
            raise ValueError(f"{task_path}: {split}[{index}] must have input and output grids")
        pairs.append(
            Pair(
                validate_grid(example["input"], f"{split}[{index}].input"),
                validate_grid(example["output"], f"{split}[{index}].output"),
            )
        )
    return pairs


def grid_width(grid: Grid, cell_size: int) -> int:
    return len(grid[0]) * cell_size + 1


def grid_height(grid: Grid, cell_size: int) -> int:
    return len(grid) * cell_size + 1


def group_width(pairs: Sequence[Pair], cell_size: int) -> int:
    columns = sum(pair.width(cell_size) for pair in pairs)
    return SECTION_PADDING * 2 + columns + PAIR_GAP * (len(pairs) - 1)


def content_width(train_pairs: Sequence[Pair], test_pairs: Sequence[Pair], cell_size: int) -> int:
    return group_width(train_pairs, cell_size) + SECTION_GAP + group_width(test_pairs, cell_size)


def choose_cell_size(train_pairs: Sequence[Pair], test_pairs: Sequence[Pair], available_width: int) -> int:
    for size in range(MAX_CELL_SIZE, MIN_CELL_SIZE - 1, -1):
        if content_width(train_pairs, test_pairs, size) <= available_width:
            return size
    return MIN_CELL_SIZE


def draw_grid(canvas: Canvas, grid: Grid, x: int, y: int, cell_size: int) -> None:
    canvas.rectangle(x, y, grid_width(grid, cell_size), grid_height(grid, cell_size), GRID_LINE)
    for row_index, row in enumerate(grid):
        for column_index, value in enumerate(row):
            canvas.rectangle(
                x + column_index * cell_size + 1,
                y + row_index * cell_size + 1,
                cell_size - 1,
                cell_size - 1,
                ARC_COLORS[value],
            )


def draw_arrow(canvas: Canvas, center_x: int, y: int) -> None:
    shaft_height = 18
    canvas.rectangle(center_x - 1, y, 3, shaft_height, INK)
    for offset in range(6):
        canvas.rectangle(center_x - 6 + offset, y + shaft_height - 6 + offset, 2, 2, INK)
        canvas.rectangle(center_x + 5 - offset, y + shaft_height - 6 + offset, 2, 2, INK)


def draw_group(
    canvas: Canvas,
    title: str,
    pairs: Sequence[Pair],
    cell_size: int,
    x: int,
    input_band_height: int,
    height: int,
    background: tuple[int, int, int],
) -> None:
    width = group_width(pairs, cell_size)
    canvas.rectangle(x, OUTER_PADDING, width, height, background)
    canvas.text(x + SECTION_PADDING, OUTER_PADDING + SECTION_PADDING, title)
    input_band_y = OUTER_PADDING + SECTION_PADDING + LABEL_HEIGHT
    arrow_y = input_band_y + input_band_height + 5
    output_band_y = input_band_y + input_band_height + ARROW_HEIGHT
    pair_x = x + SECTION_PADDING
    for pair in pairs:
        column_width = pair.width(cell_size)
        input_width = grid_width(pair.input, cell_size)
        input_height = grid_height(pair.input, cell_size)
        output_width = grid_width(pair.output, cell_size)
        input_x = pair_x + (column_width - input_width) // 2
        input_y = input_band_y + input_band_height - input_height
        output_x = pair_x + (column_width - output_width) // 2
        draw_grid(canvas, pair.input, input_x, input_y, cell_size)
        draw_arrow(canvas, pair_x + column_width // 2, arrow_y)
        draw_grid(canvas, pair.output, output_x, output_band_y, cell_size)
        pair_x += column_width + PAIR_GAP


def render_task(task_path: Path, output_path: Path, width: int) -> None:
    train_pairs = load_pairs(task_path, "train")
    test_pairs = load_pairs(task_path, "test")
    cell_size = choose_cell_size(train_pairs, test_pairs, width - OUTER_PADDING * 2)
    required_width = content_width(train_pairs, test_pairs, cell_size) + OUTER_PADDING * 2
    canvas_width = max(width, required_width)
    pairs = train_pairs + test_pairs
    input_band_height = max(grid_height(pair.input, cell_size) for pair in pairs)
    output_band_height = max(grid_height(pair.output, cell_size) for pair in pairs)
    group_height = SECTION_PADDING * 2 + LABEL_HEIGHT + input_band_height + ARROW_HEIGHT + output_band_height
    canvas = Canvas(canvas_width, group_height + OUTER_PADDING * 2, PAGE_BACKGROUND)
    groups_width = content_width(train_pairs, test_pairs, cell_size)
    train_x = (canvas_width - groups_width) // 2
    draw_group(
        canvas,
        "TRAIN",
        train_pairs,
        cell_size,
        train_x,
        input_band_height,
        group_height,
        WHITE,
    )
    test_x = train_x + group_width(train_pairs, cell_size) + SECTION_GAP
    draw_group(
        canvas,
        "TEST",
        test_pairs,
        cell_size,
        test_x,
        input_band_height,
        group_height,
        TEST_BACKGROUND,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canvas.png_bytes())


def task_paths(source: Path, requested_ids: Iterable[str]) -> list[Path]:
    requested = list(requested_ids)
    if requested:
        paths = [source / f"{task_id}.json" for task_id in requested]
        missing = [path for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError("Task JSON not found: " + ", ".join(str(path) for path in missing))
        return paths
    return sorted(source.glob("*.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Directory containing ARC task JSON files")
    parser.add_argument("--output", required=True, type=Path, help="Directory for generated PNG files")
    parser.add_argument("--task", action="append", default=[], help="Task ID to generate; repeat or omit for all")
    parser.add_argument("--width", type=int, default=960, help="Thumbnail width in pixels (default: 960)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.width < 320:
        raise ValueError("--width must be at least 320 pixels")
    paths = task_paths(args.source, args.task)
    if not paths:
        raise FileNotFoundError(f"No task JSON files found in {args.source}")
    for path in paths:
        output_path = args.output / f"{path.stem}.png"
        render_task(path, output_path, args.width)
        print(output_path)


if __name__ == "__main__":
    main()
