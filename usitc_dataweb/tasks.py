from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import RuntimeConfig
from .constants import FLOW_DEFINITIONS, Measure, TradeFlow


@dataclass(frozen=True)
class DownloadTask:
    flow: TradeFlow
    measure: Measure
    year: int
    month: int
    commodity_level: str
    hts_prefix: str | None
    filename: str

    @property
    def yyyymm(self) -> str:
        return f"{self.year}{self.month:02d}"


def _resolve_measures(config: RuntimeConfig, flow: TradeFlow) -> tuple[Measure, ...]:
    selected = config.measures.get(flow.key, "all")
    if selected == "all":
        return flow.measures

    wanted = {str(item) for item in selected}
    by_code_or_label = {measure.code: measure for measure in flow.measures}
    by_code_or_label.update({measure.label: measure for measure in flow.measures})

    missing = sorted(wanted - set(by_code_or_label))
    if missing:
        raise ValueError(f"Unknown measures for {flow.key}: {', '.join(missing)}")
    return tuple(by_code_or_label[item] for item in selected)  # type: ignore[index]


def build_tasks(config: RuntimeConfig) -> list[DownloadTask]:
    tasks: list[DownloadTask] = []
    for flow_key in config.flows:
        if flow_key not in FLOW_DEFINITIONS:
            raise ValueError(f"Unknown flow: {flow_key}")

        flow = FLOW_DEFINITIONS[flow_key]
        measures = _resolve_measures(config, flow)
        commodity_level = flow.default_level

        split_prefixes: tuple[str | None, ...]
        if config.split_strategy in {"", "none", "off", "false"}:
            split_prefixes = (None,)
        elif config.split_strategy == "hts2":
            split_prefixes = tuple(config.hts2_chapters)
        else:
            raise ValueError(f"Unsupported split strategy: {config.split_strategy}")

        for month in config.months:
            for measure in measures:
                for hts_prefix in split_prefixes:
                    filename = make_filename(flow, measure, config.year, month, hts_prefix)
                    tasks.append(
                        DownloadTask(
                            flow=flow,
                            measure=measure,
                            year=config.year,
                            month=month,
                            commodity_level=commodity_level,
                            hts_prefix=hts_prefix,
                            filename=filename,
                        )
                    )
    return tasks


def make_filename(
    flow: TradeFlow,
    measure: Measure,
    year: int,
    month: int,
    hts_prefix: str | None = None,
) -> str:
    stem = f"{flow.file_prefix}_{measure.label}_{year}{month:02d}"
    if hts_prefix:
        stem = f"{stem}_HTS{hts_prefix}"
    return f"{stem}.xlsx"


def task_output_path(output_dir: Path, task: DownloadTask) -> Path:
    return output_dir / task.flow.key / f"{task.year}{task.month:02d}" / task.filename
