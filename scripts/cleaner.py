#!/usr/bin/env python3
"""Normalize NASA Exoplanet Archive dependent values and their errors."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIRECTORY = PROJECT_ROOT / "ExoData" / "raw"
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "ExoData" / "processed"

MEASUREMENTS = {
    "FLAM": {"FLAMERR1", "FLAMERR2", "FLAMERR1_CALC", "FLAMERR2_CALC"},
    "PL_TRANDEP": {"PL_TRANDEPERR1", "PL_TRANDEPERR2"},
}
CALCULATED_ERROR_FALLBACKS = {
    "FLAMERR1": "FLAMERR1_CALC",
    "FLAMERR2": "FLAMERR2_CALC",
}
VALUE_COLUMNS = set(MEASUREMENTS) | set().union(*MEASUREMENTS.values())
SENTINELS = {"", "null", "none", "nan"}


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


def set_table_cell(characters: list[str], boundaries: list[tuple[int, int]], column_index: int, value: str) -> None:
    """Replace one fixed-width IPAC table cell without changing column widths."""
    start, end = boundaries[column_index]
    characters[start + 1:end] = value.ljust(end - start - 1)[- (end - start - 1):]


def normalize_table(source: Path, destination: Path, seen_spectra: set[tuple[str, ...]] = set()) -> bool:
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

    # Primary measurement and wavelength must be present. A row cannot participate
    # in modeling or normalization when either required value is null.
    wavelength_indexes = [i for i, name in enumerate(headers) if name == "CENTRALWAVELNG"]
    measurement_indexes = [i for i, name in enumerate(headers) if name in MEASUREMENTS]
    if len(wavelength_indexes) != 1 or len(measurement_indexes) != 1:
        raise ValueError(f"Expected one wavelength and one primary measurement in {source.name}")
    wavelength_index = wavelength_indexes[0]
    measurement_index = measurement_indexes[0]
    measurement_name = headers[measurement_index]

    cleaned_indexes: list[int] = []
    wavelength_values: set[str] = set()
    for line_index in data_indexes:
        line = lines[line_index]
        wavelength_start, wavelength_end = boundaries[wavelength_index]
        measurement_start, measurement_end = boundaries[measurement_index]
        wavelength = line[wavelength_start + 1:wavelength_end].strip()
        measurement = line[measurement_start + 1:measurement_end].strip()
        if wavelength.lower() in SENTINELS or measurement.lower() in SENTINELS:
            continue
        if numeric_value(wavelength) is None or numeric_value(measurement) is None:
            continue
        # Remove repeated wavelength rows within the same spectrum. Exact scientific
        # duplicates from separate source files are checked later by spectrum fingerprint.
        if wavelength in wavelength_values:
            continue
        wavelength_values.add(wavelength)
        cleaned_indexes.append(line_index)
    data_indexes = cleaned_indexes

    if not data_indexes:
        raise ValueError(f"No usable rows remained in {source.name}")

    # An exact raw fingerprint removes duplicate spectrum files before normalization
    # can make separately stored minima affect equality.
    fingerprint = tuple(
        (lines[index][boundaries[wavelength_index][0] + 1:boundaries[wavelength_index][1]].strip(),
         lines[index][boundaries[measurement_index][0] + 1:boundaries[measurement_index][1]].strip())
        for index in data_indexes
    )
    if fingerprint in seen_spectra:
        return False
    seen_spectra.add(fingerprint)

    # Replace missing primary uncertainties with calculated uncertainties when an
    # equivalent calculated column exists. Otherwise leave them as null for masking.
    for uncertainty_name in MEASUREMENTS[measurement_name]:
        uncertainty_index = next((i for i, name in enumerate(headers) if name == uncertainty_name), None)
        if uncertainty_index is None:
            continue
        calculated_name = CALCULATED_ERROR_FALLBACKS.get(uncertainty_name)
        calculated_index = next((i for i, name in enumerate(headers) if name == calculated_name), None) if calculated_name else None
        for line_index in data_indexes:
            characters = list(lines[line_index])
            start, end = boundaries[uncertainty_index]
            if lines[line_index][start + 1:end].strip().lower() not in SENTINELS:
                continue
            if calculated_index is None:
                continue
            calculated_start, calculated_end = boundaries[calculated_index]
            calculated_value = lines[line_index][calculated_start + 1:calculated_end]
            if calculated_value.strip().lower() not in SENTINELS:
                set_table_cell(characters, boundaries, uncertainty_index, calculated_value.strip())
                lines[line_index] = "".join(characters)

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

    # Find the primary measurement range. Uncertainties use the same range below;
    # unlike uncertainties, measurements are shifted by their minimum before scaling.
    column_ranges: dict[int, tuple[float, float]] = {}
    for column_index, values in column_values.items():
        if values:
            minimum = min(value for _, value in values)
            maximum = max(value for _, value in values)
            if maximum > minimum:
                column_ranges[column_index] = (minimum, maximum)

    measurement_range = column_ranges.get(measurement_index)

    # Scaling uncertainties by the measurement range without min subtraction preserves
    # their physical meaning. Null/undefined uncertainties remain null for later masking.
    for line_index in data_indexes:
        line = lines[line_index]
        characters = list(line)
        if measurement_range is not None:
            minimum, maximum = measurement_range
            start, end = boundaries[measurement_index]
            value = numeric_value(line[start + 1:end])
            if value is not None:
                normalized = (value - minimum) / (maximum - minimum)
                set_table_cell(characters, boundaries, measurement_index, format_number(normalized, end - start - 1))

            scale = maximum - minimum
            for uncertainty_name in MEASUREMENTS[measurement_name]:
                uncertainty_index = next((i for i, name in enumerate(headers) if name == uncertainty_name), None)
                if uncertainty_index is None:
                    continue
                start, end = boundaries[uncertainty_index]
                value = numeric_value(line[start + 1:end])
                if value is not None:
                    set_table_cell(characters, boundaries, uncertainty_index, format_number(value / scale, end - start - 1))
        lines[line_index] = "".join(characters)

    # Rebuild the file without unusable or duplicate rows. Lines before the units
    # row, the units/type block, and footer metadata are always preserved.
    original_data_indexes = set(line_index for line_index in range(header_index + 3, len(lines)) if lines[line_index] and not lines[line_index].startswith(("\\", "|")))
    kept_lines = set(data_indexes)
    output_lines = [
        line for index, line in enumerate(lines)
        if index <= header_index + 2
        or index not in original_data_indexes
        or index in kept_lines
    ]

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(output_lines) + "\n")
    return True


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
    seen_spectra: set[tuple[str, ...]] = set()
    for source in files:
        try:
            if normalize_table(source, output_directory / source.name, seen_spectra):
                processed += 1
        except (OSError, ValueError) as error:
            # Keep processing the collection when one malformed table cannot be read.
            print(f"Skipping {source.name}: {error}")

    print(f"Normalized {processed} files into {output_directory}")
    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
