"""SEG-Y file reader using segyio with fallback strategies."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import segyio

from segy_toolbox.io.ebcdic import decode_textual_header, detect_encoding
from segy_toolbox.models import FORMAT_BPS, SegyFileInfo

# ---------------------------------------------------------------------------
# Binary Header field mapping: name -> (BinField enum, dtype description)
# ---------------------------------------------------------------------------

BINARY_FIELD_MAP: dict[str, tuple[int, str, int]] = {
    # name: (segyio.BinField enum value, dtype, byte_offset_from_3200)
    "job_id":                   (segyio.BinField.JobID, "int32", 1),
    "line_number":              (segyio.BinField.LineNumber, "int32", 5),
    "reel_number":              (segyio.BinField.ReelNumber, "int32", 9),
    "traces_per_ensemble":      (segyio.BinField.Traces, "int16", 13),
    "aux_traces_per_ensemble":  (segyio.BinField.AuxTraces, "int16", 15),
    "sample_interval":          (segyio.BinField.Interval, "int16", 17),
    "sample_interval_original": (segyio.BinField.IntervalOriginal, "int16", 19),
    "samples_per_trace":        (segyio.BinField.Samples, "int16", 21),
    "samples_per_trace_orig":   (segyio.BinField.SamplesOriginal, "int16", 23),
    "format_code":              (segyio.BinField.Format, "int16", 25),
    "ensemble_fold":            (segyio.BinField.EnsembleFold, "int16", 27),
    "trace_sorting":            (segyio.BinField.SortingCode, "int16", 29),
    "vertical_sum":             (segyio.BinField.VerticalSum, "int16", 31),
    "sweep_freq_start":         (segyio.BinField.SweepFrequencyStart, "int16", 33),
    "sweep_freq_end":           (segyio.BinField.SweepFrequencyEnd, "int16", 35),
    "sweep_length":             (segyio.BinField.SweepLength, "int16", 37),
    "sweep_type":               (segyio.BinField.Sweep, "int16", 39),
    "sweep_trace_number":       (segyio.BinField.SweepChannel, "int16", 41),
    "sweep_taper_start":        (segyio.BinField.SweepTaperStart, "int16", 43),
    "sweep_taper_end":          (segyio.BinField.SweepTaperEnd, "int16", 45),
    "taper_type":               (segyio.BinField.Taper, "int16", 47),
    "correlated":               (segyio.BinField.CorrelatedTraces, "int16", 49),
    "binary_gain":              (segyio.BinField.BinaryGainRecovery, "int16", 51),
    "amplitude_recovery":       (segyio.BinField.AmplitudeRecovery, "int16", 53),
    "measurement_system":       (segyio.BinField.MeasurementSystem, "int16", 55),
    "impulse_polarity":         (segyio.BinField.ImpulseSignalPolarity, "int16", 57),
    "vibratory_polarity":       (segyio.BinField.VibratoryPolarity, "int16", 59),
    "segy_revision":            (segyio.BinField.SEGYRevision, "int16", 301),
    "fixed_length_trace":       (segyio.BinField.TraceFlag, "int16", 303),
    "extended_headers":         (segyio.BinField.ExtendedHeaders, "int16", 305),
}

# ---------------------------------------------------------------------------
# Trace Header field mapping: name -> (TraceField enum, dtype, byte_offset)
# ---------------------------------------------------------------------------

TRACE_FIELD_MAP: dict[str, tuple[int, str, int]] = {
    "trace_sequence_line":          (segyio.TraceField.TRACE_SEQUENCE_LINE, "int32", 1),
    "trace_sequence_file":          (segyio.TraceField.TRACE_SEQUENCE_FILE, "int32", 5),
    "field_record":                 (segyio.TraceField.FieldRecord, "int32", 9),
    "trace_number":                 (segyio.TraceField.TraceNumber, "int32", 13),
    "energy_source_point":          (segyio.TraceField.EnergySourcePoint, "int32", 17),
    "cdp":                          (segyio.TraceField.CDP, "int32", 21),
    "cdp_trace":                    (segyio.TraceField.TRACE_SAMPLE_COUNT, "int32", 25),
    "trace_id":                     (segyio.TraceField.TraceIdentificationCode, "int16", 29),
    "vertically_summed":            (segyio.TraceField.NSummedTraces, "int16", 31),
    "horizontally_stacked":         (segyio.TraceField.NStackedTraces, "int16", 33),
    "data_use":                     (segyio.TraceField.DataUse, "int16", 35),
    "offset":                       (segyio.TraceField.offset, "int32", 37),
    "receiver_elevation":           (segyio.TraceField.ReceiverGroupElevation, "int32", 41),
    "source_surface_elevation":     (segyio.TraceField.SourceSurfaceElevation, "int32", 45),
    "source_depth":                 (segyio.TraceField.SourceDepth, "int32", 49),
    "datum_elevation_receiver":     (segyio.TraceField.ReceiverDatumElevation, "int32", 53),
    "datum_elevation_source":       (segyio.TraceField.SourceDatumElevation, "int32", 57),
    "water_depth_source":           (segyio.TraceField.SourceWaterDepth, "int32", 61),
    "water_depth_receiver":         (segyio.TraceField.GroupWaterDepth, "int32", 65),
    "elevation_scalar":             (segyio.TraceField.ElevationScalar, "int16", 69),
    "coordinate_scalar":            (segyio.TraceField.SourceGroupScalar, "int16", 71),
    "source_x":                     (segyio.TraceField.SourceX, "int32", 73),
    "source_y":                     (segyio.TraceField.SourceY, "int32", 77),
    "group_x":                      (segyio.TraceField.GroupX, "int32", 81),
    "group_y":                      (segyio.TraceField.GroupY, "int32", 85),
    "coordinate_units":             (segyio.TraceField.CoordinateUnits, "int16", 89),
    "weathering_velocity":          (segyio.TraceField.WeatheringVelocity, "int16", 91),
    "subweathering_velocity":       (segyio.TraceField.SubWeatheringVelocity, "int16", 93),
    "uphole_time_source":           (segyio.TraceField.SourceUpholeTime, "int16", 95),
    "uphole_time_receiver":         (segyio.TraceField.GroupUpholeTime, "int16", 97),
    "source_static":                (segyio.TraceField.SourceStaticCorrection, "int16", 99),
    "receiver_static":              (segyio.TraceField.GroupStaticCorrection, "int16", 101),
    "total_static":                 (segyio.TraceField.TotalStaticApplied, "int16", 103),
    "lag_time_a":                   (segyio.TraceField.LagTimeA, "int16", 105),
    "lag_time_b":                   (segyio.TraceField.LagTimeB, "int16", 107),
    "delay_recording_time":         (segyio.TraceField.DelayRecordingTime, "int16", 109),
    "mute_time_start":              (segyio.TraceField.MuteTimeStart, "int16", 111),
    "mute_time_end":                (segyio.TraceField.MuteTimeEND, "int16", 113),
    "samples":                      (segyio.TraceField.TRACE_SAMPLE_COUNT, "int16", 115),
    "sample_interval":              (segyio.TraceField.TRACE_SAMPLE_INTERVAL, "int16", 117),
    "inline":                       (segyio.TraceField.INLINE_3D, "int32", 189),
    "crossline":                    (segyio.TraceField.CROSSLINE_3D, "int32", 193),
    "shotpoint":                    (segyio.TraceField.ShotPoint, "int32", 197),
    "shotpoint_scalar":             (segyio.TraceField.ShotPointScalar, "int16", 201),
    "cdp_x":                        (segyio.TraceField.CDP_X, "int32", 181),
    "cdp_y":                        (segyio.TraceField.CDP_Y, "int32", 185),
}


class SegyFileReader:
    """Read SEG-Y files with multiple fallback strategies."""

    def open(self, path: str) -> SegyFileInfo:
        """Open a SEG-Y file read-only and extract all metadata."""
        path = str(path)
        file_size = os.path.getsize(path)
        filename = Path(path).name

        info = SegyFileInfo(
            path=path,
            filename=filename,
            file_size_bytes=file_size,
        )

        # Read raw EBCDIC header
        with open(path, "rb") as fp:
            raw_header = fp.read(3200)
        info.ebcdic_raw = raw_header
        info.ebcdic_encoding = detect_encoding(raw_header)
        info.ebcdic_lines = decode_textual_header(raw_header)

        # Open with segyio (fallback chain)
        f = self._open_segyio(path)
        try:
            self._extract_binary_header(f, info)
            self._extract_trace_info(f, info)
            self._calculate_expected_size(info)
        finally:
            f.close()

        return info

    def read_all_trace_headers(
        self, path: str, fields: list[str] | None = None
    ) -> pd.DataFrame:
        """Read specified trace header fields from ALL traces into a DataFrame."""
        if fields is None:
            fields = [
                "trace_sequence_line", "source_x", "source_y",
                "group_x", "group_y", "cdp_x", "cdp_y",
                "coordinate_scalar", "elevation_scalar",
                "inline", "crossline", "offset",
                "delay_recording_time", "samples", "sample_interval",
            ]

        f = self._open_segyio(path)
        try:
            data: dict[str, list] = {"trace_index": list(range(f.tracecount))}
            for field_name in fields:
                if field_name not in TRACE_FIELD_MAP:
                    continue
                enum_val = TRACE_FIELD_MAP[field_name][0]
                try:
                    values = f.attributes(enum_val)[:]
                    data[field_name] = list(values)
                except Exception:
                    data[field_name] = [0] * f.tracecount
        finally:
            f.close()

        return pd.DataFrame(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _open_segyio(path: str) -> segyio.SegyFile:
        """Open SEG-Y with fallback strategies."""
        strategies = [
            {"strict": False},
            {"strict": False, "ignore_geometry": True},
            {"strict": False, "endian": "little"},
            {"strict": False, "ignore_geometry": True, "endian": "little"},
        ]
        last_error = None
        for kwargs in strategies:
            try:
                return segyio.open(path, "r", **kwargs)
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(
            f"Cannot open SEG-Y file with any strategy: {last_error}"
        )

    @staticmethod
    def _extract_binary_header(f: segyio.SegyFile, info: SegyFileInfo) -> None:
        """Extract binary file header fields."""
        for name, (enum_val, dtype, offset) in BINARY_FIELD_MAP.items():
            try:
                info.binary_header[name] = int(f.bin[enum_val])
            except Exception:
                info.binary_header[name] = 0

        info.format_code = info.binary_header.get("format_code", 0)
        info.sample_interval = info.binary_header.get("sample_interval", 0)
        info.samples_per_trace = info.binary_header.get("samples_per_trace", 0)
        info.bytes_per_sample = FORMAT_BPS.get(info.format_code, 4)

    @staticmethod
    def _extract_trace_info(f: segyio.SegyFile, info: SegyFileInfo) -> None:
        """Extract trace count and sampled trace header statistics."""
        info.trace_count = f.tracecount

        if info.samples_per_trace == 0 and f.tracecount > 0:
            info.samples_per_trace = len(f.samples)

        # Coordinate scalar from first trace
        try:
            info.coordinate_scalar = f.header[0][segyio.TraceField.SourceGroupScalar]
        except Exception:
            info.coordinate_scalar = 0

        # Sample trace header statistics for key fields
        stat_fields = {
            # Sequence & identification
            "trace_sequence_line": segyio.TraceField.TRACE_SEQUENCE_LINE,
            "trace_sequence_file": segyio.TraceField.TRACE_SEQUENCE_FILE,
            "field_record": segyio.TraceField.FieldRecord,
            "trace_number": segyio.TraceField.TraceNumber,
            "energy_source_point": segyio.TraceField.EnergySourcePoint,
            "trace_id": segyio.TraceField.TraceIdentificationCode,
            # CDP / Ensemble
            "cdp": segyio.TraceField.CDP,
            "cdp_trace": segyio.TraceField.TRACE_SAMPLE_COUNT,
            "offset": segyio.TraceField.offset,
            # Coordinates
            "source_x": segyio.TraceField.SourceX,
            "source_y": segyio.TraceField.SourceY,
            "group_x": segyio.TraceField.GroupX,
            "group_y": segyio.TraceField.GroupY,
            "cdp_x": segyio.TraceField.CDP_X,
            "cdp_y": segyio.TraceField.CDP_Y,
            "coordinate_scalar": segyio.TraceField.SourceGroupScalar,
            # Elevation & depth
            "elevation_scalar": segyio.TraceField.ElevationScalar,
            "receiver_elevation": segyio.TraceField.ReceiverGroupElevation,
            "source_surface_elevation": segyio.TraceField.SourceSurfaceElevation,
            "source_depth": segyio.TraceField.SourceDepth,
            "water_depth_source": segyio.TraceField.SourceWaterDepth,
            "water_depth_receiver": segyio.TraceField.GroupWaterDepth,
            # 3D geometry
            "inline": segyio.TraceField.INLINE_3D,
            "crossline": segyio.TraceField.CROSSLINE_3D,
            "shotpoint": segyio.TraceField.ShotPoint,
            "shotpoint_scalar": segyio.TraceField.ShotPointScalar,
            # Timing & sampling
            "delay_recording_time": segyio.TraceField.DelayRecordingTime,
            "samples": segyio.TraceField.TRACE_SAMPLE_COUNT,
            "sample_interval": segyio.TraceField.TRACE_SAMPLE_INTERVAL,
            # Statics
            "source_static": segyio.TraceField.SourceStaticCorrection,
            "receiver_static": segyio.TraceField.GroupStaticCorrection,
            "total_static": segyio.TraceField.TotalStaticApplied,
        }
        for name, enum_val in stat_fields.items():
            try:
                values = f.attributes(enum_val)[:]
                arr = np.array(values, dtype=np.float64)
                info.trace_header_summary[name] = {
                    "min": float(arr.min()),
                    "max": float(arr.max()),
                    "mean": float(arr.mean()),
                    "std": float(arr.std()),
                }
            except Exception:
                info.trace_header_summary[name] = {
                    "min": 0, "max": 0, "mean": 0, "std": 0
                }

    @staticmethod
    def _calculate_expected_size(info: SegyFileInfo) -> None:
        """Calculate expected file size from header metadata."""
        if info.samples_per_trace > 0 and info.bytes_per_sample > 0:
            trace_bytes = 240 + info.samples_per_trace * info.bytes_per_sample
            info.expected_file_size = 3200 + 400 + trace_bytes * info.trace_count
        else:
            info.expected_file_size = 0
