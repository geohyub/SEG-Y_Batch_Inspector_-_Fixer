"""Pipeline orchestrator: Read -> Validate -> Edit -> Validate -> Write."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from segy_toolbox.config import EditConfig
from segy_toolbox.core.validator import SegyValidator
from segy_toolbox.io.reader import SegyFileReader
from segy_toolbox.io.writer import SegyFileWriter
from segy_toolbox.models import (
    BatchResult,
    ChangeRecord,
    EditJob,
    PipelineState,
    SegyFileInfo,
    ValidationResult,
)


class SegyEngine:
    """Orchestrates the full Read -> Validate -> Edit -> Validate -> Write pipeline."""

    STAGES = [
        (0, "파일 읽기"),
        (1, "사전 검증"),
        (2, "출력 준비"),
        (3, "수정 적용"),
        (4, "사후 검증"),
        (5, "리포트 생성"),
    ]

    def __init__(self, config: EditConfig | None = None):
        self.config = config or EditConfig()
        self.reader = SegyFileReader()
        self.writer = SegyFileWriter()
        self.validator = SegyValidator(
            coordinate_bounds=self.config.coordinate_bounds or None,
            check_structure=self.config.check_file_structure,
            check_binary_header=self.config.check_binary_header,
            check_trace_header=self.config.check_trace_header,
            check_coordinate_range=self.config.check_coordinate_range,
        )
        self._state = PipelineState.IDLE
        self._on_stage: Callable[[int, str], None] | None = None
        self._on_progress: Callable[[int, int], None] | None = None
        self._on_log: Callable[[str], None] | None = None
        self._cancelled = False

    def set_callbacks(
        self,
        on_stage: Callable[[int, str], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self._on_stage = on_stage
        self._on_progress = on_progress
        self._on_log = on_log

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def state(self) -> PipelineState:
        return self._state

    # ------------------------------------------------------------------
    # Individual pipeline stages
    # ------------------------------------------------------------------

    def load_file(self, path: str) -> SegyFileInfo:
        """Stage 0: Read file and extract metadata."""
        self._emit_stage(0)
        self._log(f"파일 읽기: {Path(path).name}")
        info = self.reader.open(path)
        self._state = PipelineState.FILES_LOADED
        self._log(f"로드 완료: {info.trace_count} traces, {info.samples_per_trace} samples")
        return info

    def validate(self, info: SegyFileInfo) -> ValidationResult:
        """Stage 1: Run pre-edit validation."""
        self._emit_stage(1)
        self._log("사전 검증 실행 중...")
        result = self.validator.validate(info)

        if result.overall_status == "FAIL":
            self._state = PipelineState.FILES_LOADED
            self._log(f"검증 실패: {sum(1 for c in result.checks if c.status == 'FAIL')} 항목")
        else:
            self._state = PipelineState.VALIDATED
            self._log(f"검증 완료: {result.overall_status}")

        return result

    def preview(self, path: str, job: EditJob) -> dict:
        """Dry run: preview all changes without modifying the file."""
        self._log("Dry Run 미리보기 생성 중...")
        return self.writer.dry_run(path, job)

    def apply(
        self,
        path: str,
        job: EditJob,
    ) -> tuple[str, list[ChangeRecord], ValidationResult | None]:
        """Stages 2-4: Prepare output, apply edits, post-validate.

        Returns (output_path, changes, post_validation_result).
        """
        filename = Path(path).name

        # Stage 2: Prepare output
        self._emit_stage(2)
        self._log("출력 파일 준비 중...")
        output_path = self.writer.prepare_output(
            path,
            output_mode=self.config.output_mode,
            output_dir=self.config.output_dir,
        )
        self._log(f"출력 경로: {output_path}")

        # Stage 3: Apply edits
        self._emit_stage(3)
        self._log("수정 적용 중...")

        def _on_trace_progress(current: int, total: int) -> None:
            if self._on_progress and current % 500 == 0:
                self._on_progress(current, total)

        # Throttle change logging to avoid overwhelming the GUI thread.
        # Only log first few changes and a summary instead of every single one.
        _change_log_count = 0

        def _on_change_throttled(c: ChangeRecord) -> None:
            nonlocal _change_log_count
            _change_log_count += 1
            if _change_log_count <= 5:
                self._log(
                    f"  {c.field_type}/{c.field_name}: "
                    f"{c.before_value} -> {c.after_value}"
                )
            elif _change_log_count == 6:
                self._log("  ... (이후 변경사항은 완료 후 요약됩니다)")

        changes = self.writer.apply_edits(
            output_path,
            job,
            filename=filename,
            on_change=_on_change_throttled,
            on_progress=_on_trace_progress,
        )
        self._log(f"수정 완료: {len(changes)} 건 변경")

        # Stage 4: Post-edit validation
        self._emit_stage(4)
        self._log("사후 검증 실행 중...")
        new_info = self.reader.open(output_path)
        post_result = self.validator.validate(new_info)
        self._log(f"사후 검증: {post_result.overall_status}")

        self._state = PipelineState.APPLIED
        return output_path, changes, post_result

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def run_batch(
        self,
        paths: list[str],
        job: EditJob,
    ) -> list[BatchResult]:
        """Run the full pipeline on multiple files."""
        self._cancelled = False
        results: list[BatchResult] = []

        for i, path in enumerate(paths):
            if self._cancelled:
                results.append(BatchResult(
                    filename=Path(path).name,
                    status="SKIPPED",
                    message="작업 취소됨",
                ))
                continue

            if self._on_progress:
                self._on_progress(i, len(paths))

            start_time = time.time()
            filename = Path(path).name

            try:
                # Load
                info = self.load_file(path)

                # Pre-validate
                pre_val = self.validate(info)
                if pre_val.overall_status == "FAIL":
                    results.append(BatchResult(
                        filename=filename,
                        status="SKIPPED",
                        message="사전 검증 실패로 건너뜀",
                        validation_before=pre_val,
                        duration_seconds=time.time() - start_time,
                    ))
                    continue

                # Apply
                _, changes, post_val = self.apply(path, job)
                results.append(BatchResult(
                    filename=filename,
                    status="SUCCESS",
                    message=f"{len(changes)} 건 변경 적용",
                    changes=changes,
                    validation_before=pre_val,
                    validation_after=post_val,
                    duration_seconds=time.time() - start_time,
                ))

            except Exception as e:
                results.append(BatchResult(
                    filename=filename,
                    status="FAILURE",
                    message=str(e),
                    duration_seconds=time.time() - start_time,
                ))

        if self._on_progress:
            self._on_progress(len(paths), len(paths))

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit_stage(self, stage_idx: int) -> None:
        if self._on_stage and stage_idx < len(self.STAGES):
            self._on_stage(stage_idx, self.STAGES[stage_idx][1])

    def _log(self, message: str) -> None:
        if self._on_log:
            self._on_log(message)
