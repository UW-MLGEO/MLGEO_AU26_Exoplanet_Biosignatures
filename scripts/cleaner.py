#!/usr/bin/env python3
"""Normalize NASA Exoplanet Archive dependent values and their errors."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIRECTORY = PROJECT_ROOT / "ExoData" / "raw"
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "ExoData" / "processed"

VALUE_COLUMNS = {
    "FLAM",
    "FLAMERR1",
    "FLAMERR2",
    "FLAMERR1_CALC",
    "FLAMERR2_CALC",
    "PL_TRANDEP",
    "PL_TRANDEPERR1",
    "PL_TRANDEPERR2",
}


def numeric_value(value: str) -> float | None:
    """Convert a table value to a number without changing sentinel values."""
    try:
        number = float(value.strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def column_boundaries(header_line: str) -> list[tuple[int, int]]:
    separators = [index for index, character in enumerate(header_line) if character == "|"]
    return list(zip(separators, separators[1:]))


def column_names(header_line: str) -> list[str]:
    boundaries = column_boundaries(header_line)
    return [
        header_line[start + 1:end].strip()
        for start, end in boundaries
    ]


def format_number(value: float, width: int) -> str:
    text = format(value, ".10g")
    if len(text) > width:
        text = format(value, ".6g")
    return text.rjust(width)[-width:]


def normalize_table(source: Path, destination: Path) -> None:
    lines = source.read_text().splitlines()

    # IPAC tables store metadata first and put column names, data types, and units on the next three |---| delimited lines.
    header_index = next(
        index for index, line in enumerate(lines)
        if line.startswith("|") and ("PL_TRANDEP" in line or "FLAM" in line)
    )
    headers = column_names(lines[header_index])
    boundaries = column_boundaries(lines[header_index])

    # Only normalize physical dependent values and uncertainty/error columns.
    normalized_columns = {
        index for index, name in enumerate(headers) if name in VALUE_COLUMNS
    }
    if not normalized_columns:
        raise ValueError(f"No dependent-value columns found in {source.name}")

    data_indexes = [
        index for index, line in enumerate(lines[header_index + 1:], start=header_index + 1)
        if line and not line.startswith(("\\", "|"))
    ]

    # Replace the units for normalized columns with 'arbitrary' because their original physical units no longer describe values scaled to the interval [0, 1].
    units_index = header_index + 2
    units_characters = list(lines[units_index])
    for column_index in normalized_columns:
        start, end = boundaries[column_index]
        replacement = "arbitrary".ljust(end - start - 1)[- (end - start - 1):]
        units_characters[start + 1:end] = replacement
    lines[units_index] = "".join(units_characters)

    column_values: dict[int, list[tuple[int, float]]] = {
        index: [] for index in normalized_columns
    }
    for line_index in data_indexes:
        line = lines[line_index]
        for column_index in normalized_columns:
            start, end = boundaries[column_index]
            value = numeric_value(line[start + 1:end])
            if value is not None:
                column_values[column_index].append((line_index, value))

    # Find each column's range independently so every spectrum is min-max scaled.
    column_ranges: dict[int, tuple[float, float]] = {}
    for column_index, values in column_values.items():
        if values:
            minimum = min(value for _, value in values)
            maximum = max(value for _, value in values)
            if maximum > minimum:
                column_ranges[column_index] = (minimum, maximum)

    # Constant columns cannot be scaled without division by zero and remain
    # unchanged. All other valid values use normalized = (x - min) / (max - min).
    for line_index in data_indexes:
        line = lines[line_index]
        characters = list(line)
        for column_index, (minimum, maximum) in column_ranges.items():
            start, end = boundaries[column_index]
            value = numeric_value(line[start + 1:end])
            if value is None:
                continue
            normalized = (value - minimum) / (maximum - minimum)
            replacement = format_number(normalized, end - start - 1)
            characters[start + 1:end] = replacement
        lines[line_index] = "".join(characters)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_directory", nargs="?", type=Path, default=DEFAULT_INPUT_DIRECTORY)
    parser.add_argument("output_directory", nargs="?", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    args = parser.parse_args()

    input_directory = args.input_directory.resolve()
    output_directory = args.output_directory.resolve()
    files = sorted(input_directory.glob("*.tbl"))

    if not files:
        print(f"No .tbl files found in {input_directory}")
        return 1

    processed = 0
    for source in files:
        try:
            normalize_table(source, output_directory / source.name)
            processed += 1
        except (OSError, ValueError) as error:
            # Keep processing the collection when one malformed table cannot be read.
            print(f"Skipping {source.name}: {error}")

    print(f"Normalized {processed} files into {output_directory}")
    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
