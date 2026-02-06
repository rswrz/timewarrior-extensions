#!/usr/bin/env python3

"""Shared helpers for Dynamics report extensions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
try:
    import json5 as json
except ImportError:
    import json
import math
import os
import socket
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib import error as urlerror, request as urlrequest

TIMEW_DATETIME_FORMAT = "%Y%m%dT%H%M%S%z"
DEFAULT_ANNOTATION_DELIMITER = "; "
DEFAULT_OUTPUT_SEPARATOR = "\n"
DEFAULT_CONFIG_FILENAME = ".dynamics_config.json"
DEFAULT_TYPE = "Work"
MAX_DESCRIPTION_LENGTH = 500

CONFIG_FILE_KEY = "reports.dynamics.config_file"
ANNOTATION_DELIMITER_KEY = "reports.dynamics.annotation_delimiter"
OUTPUT_SEPARATOR_KEY = "reports.dynamics.annotation_output_separator"
EXCLUDE_TAGS_KEY = "reports.dynamics.exclude_tags"
ABSORB_TAG_KEY = "reports.dynamics.absorb_tag"

LLM_ENABLED_KEY = "reports.dynamics.llm.enabled"
LLM_PROVIDER_KEY = "reports.dynamics.llm.provider"
LLM_ENDPOINT_KEY = "reports.dynamics.llm.endpoint"
LLM_MODEL_KEY = "reports.dynamics.llm.model"
LLM_TEMPERATURE_KEY = "reports.dynamics.llm.temperature"
LLM_TIMEOUT_KEY = "reports.dynamics.llm.timeout"
LLM_OPENAI_API_KEY_KEY = "reports.dynamics.llm.openai_api_key"

DEFAULT_LLM_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
DEFAULT_LLM_MODEL = "llama3"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_LLM_TEMPERATURE = 0.2
DEFAULT_LLM_TIMEOUT = 2.0


@dataclass
class LLMConfig:
    enabled: bool
    provider: str
    endpoint: str
    model: str
    temperature: float
    timeout: float
    api_key: Optional[str]


@dataclass
class DynamicsConfig:
    config_file: str
    annotation_delimiter_override: Optional[str]
    annotation_output_separator_override: Optional[str]
    exclude_tags: set[str]
    absorb_tag: Optional[str]
    llm: LLMConfig


@dataclass
class AbsorptionDayReport:
    date: str
    slack_seconds: int
    admin_raw_seconds: int
    absorbed_seconds: int
    leftover_raw_seconds: int
    leftover_exported_minutes: int


@dataclass
class DynamicsRecord:
    date: str
    duration_minutes: int
    project: str
    project_task: str
    project_display: str
    project_task_display: str
    role: str
    type: str
    description: str
    external_comment: str
    annotation_delimiter: str
    output_separator: str
    llm_settings: Dict[str, Any] = field(default_factory=dict)

    def as_csv_row(self) -> List[str]:
        return [
            self.date,
            str(self.duration_minutes),
            self.project,
            self.project_task,
            self.role,
            self.type,
            self.description,
            self.external_comment,
        ]


class LLMRefiner:
    """Refine descriptions using an optional LLM backend (local or remote)."""

    SYSTEM_PROMPT = (
        "You rewrite time tracking descriptions for clarity while keeping the original meaning. "
        "You must respond with JSON only."
    )

    def __init__(
        self,
        enabled: bool,
        endpoint: str,
        model: str,
        temperature: float,
        timeout: float,
        provider: str,
        api_key: Optional[str],
    ) -> None:
        self.enabled = enabled
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.provider = provider
        self.api_key = api_key
        self._cache: Dict[Tuple[Any, ...], str] = {}

    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMRefiner":
        return cls(
            enabled=config.enabled,
            endpoint=config.endpoint,
            model=config.model,
            temperature=config.temperature,
            timeout=config.timeout,
            provider=config.provider,
            api_key=config.api_key,
        )

    def refine(
        self,
        description: str,
        delimiter: Optional[str],
        output_separator: str,
        context: Dict[str, str],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.enabled:
            return description

        overrides = overrides or {}
        override_enabled = overrides.get("enabled")
        if override_enabled is False:
            return description

        effective_model = overrides.get("model", self.model)
        effective_temperature = overrides.get("temperature", self.temperature)
        effective_endpoint = overrides.get("endpoint", self.endpoint)
        effective_timeout = overrides.get("timeout", self.timeout)
        effective_provider = str(overrides.get("provider", self.provider)).strip().lower()
        if effective_provider not in {"ollama", "openai"}:
            effective_provider = self.provider
        effective_api_key = overrides.get("api_key", self.api_key)

        if effective_provider == "openai":
            effective_endpoint = effective_endpoint or DEFAULT_OPENAI_ENDPOINT
            effective_model = effective_model or DEFAULT_OPENAI_MODEL
        else:
            effective_endpoint = effective_endpoint or DEFAULT_LLM_ENDPOINT
            effective_model = effective_model or DEFAULT_LLM_MODEL

        try:
            effective_temperature = float(effective_temperature)
        except (TypeError, ValueError):
            effective_temperature = self.temperature

        try:
            effective_timeout = float(effective_timeout)
        except (TypeError, ValueError):
            effective_timeout = self.timeout

        if not effective_model or not effective_endpoint:
            return description
        if effective_provider == "openai" and not effective_api_key:
            return description

        delimiter = delimiter or ""
        segments = [description] if not delimiter else description.split(delimiter)
        if not segments:
            return description

        hidden_mask = []
        visible_segments: List[str] = []
        for segment in segments:
            is_hidden = segment.startswith("++") and segment.endswith("++")
            hidden_mask.append(is_hidden)
            if not is_hidden:
                visible_segments.append(segment.strip())

        if not visible_segments:
            return description

        cache_key = (
            description,
            delimiter,
            output_separator,
            effective_model,
            round(float(effective_temperature), 3),
            effective_provider,
            effective_endpoint,
            tuple(sorted((k, v) for k, v in context.items() if v)),
            tuple(visible_segments),
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = self._build_prompt(
            description, visible_segments, delimiter, output_separator, context
        )
        if effective_provider == "openai":
            payload: Dict[str, Any] = {
                "model": effective_model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": float(effective_temperature),
            }
        else:
            payload = {
                "model": effective_model,
                "prompt": prompt,
                "system": self.SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": float(effective_temperature)},
            }

        try:
            refined_segments = self._call_model(
                payload,
                effective_endpoint,
                effective_timeout,
                effective_provider,
                effective_api_key,
            )
        except Exception:
            return description

        if refined_segments is None or len(refined_segments) != len(visible_segments):
            return description

        visible_iter = iter(refined_segments)
        reconstructed: List[str] = []
        for is_hidden, original in zip(hidden_mask, segments):
            if is_hidden:
                reconstructed.append(original)
                continue

            candidate = next(visible_iter)
            if not isinstance(candidate, str):
                return description
            cleaned = candidate.strip()
            if not cleaned:
                cleaned = original.strip()
            reconstructed.append(cleaned)

        if delimiter:
            refined_description = delimiter.join(reconstructed)
        else:
            refined_description = reconstructed[0] if reconstructed else description

        self._cache[cache_key] = refined_description
        return refined_description

    @staticmethod
    def _build_prompt(
        description: str,
        segments: Sequence[str],
        delimiter: str,
        output_separator: str,
        context: Dict[str, str],
    ) -> str:
        context_lines = [
            f"{key.title()}: {value}" for key, value in context.items() if value
        ]
        context_block = "\n".join(context_lines) if context_lines else "None"
        segments_json = json.dumps(list(segments), ensure_ascii=False)

        instructions = (
            "Rewrite each segment for clarity while keeping the original meaning. "
            "Return a JSON array with exactly {count} strings in the same order. "
            "Do not add, remove, or reorder segments. Keep numbers, IDs, and names unchanged. "
            "Each string must stay concise and professional. Respond with JSON only."
        ).format(count=len(segments))

        prompt = (
            f"{instructions}\n\n"
            f"Delimiter: {delimiter or '[none]'}\n"
            f"Output separator: {output_separator}\n"
            f"Context:\n{context_block}\n\n"
            f"Original description string:\n{description}\n\n"
            f"Segments JSON:\n{segments_json}\n"
        )
        return prompt

    def _call_model(
        self,
        payload: Dict[str, Any],
        endpoint: str,
        timeout: float,
        provider: str,
        api_key: Optional[str],
    ) -> Optional[List[str]]:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if provider == "openai" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request_obj = urlrequest.Request(endpoint, data=data, headers=headers)

        try:
            with urlrequest.urlopen(request_obj, timeout=float(timeout)) as response:
                raw = response.read().decode("utf-8")
        except (urlerror.URLError, socket.timeout):
            raise

        try:
            response_json = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON from LLM endpoint") from exc

        if provider == "openai":
            choices = response_json.get("choices")
            if not isinstance(choices, list) or not choices:
                return None
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                return None
            message = first_choice.get("message")
            if not isinstance(message, dict):
                return None
            output = message.get("content", "")
        else:
            output = response_json.get("response")
        if not isinstance(output, str):
            return None

        output = output.strip()
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, list):
            return None

        return [str(item) for item in parsed]


def split_report_input(stream: Iterable[str]) -> Tuple[Dict[str, str], str]:
    """Split Timewarrior report header from JSON payload."""

    content = "".join(stream)
    if "\n\n" not in content:
        return {}, content

    header_text, payload = content.split("\n\n", 1)
    if not header_text.strip() or header_text.lstrip().startswith("["):
        return {}, content

    header_lines = header_text.splitlines()
    if not any(": " in line for line in header_lines):
        return {}, content

    config: Dict[str, str] = {}
    for line in header_lines:
        if not line.strip():
            continue
        key, _, remainder = line.partition(": ")
        if not key:
            continue
        config[key.strip()] = remainder.rstrip("\n")

    return config, payload


def parse_timew_export(payload: str) -> List[dict]:
    """Parse the JSON payload produced by `timew export`."""

    return json.loads(payload) if payload else []


def resolve_report_config(header: Dict[str, str]) -> DynamicsConfig:
    annotation_delimiter_override = _resolve_override_value(header, ANNOTATION_DELIMITER_KEY)
    output_separator_override = _resolve_override_value(header, OUTPUT_SEPARATOR_KEY)

    config_file = _resolve_value(header, CONFIG_FILE_KEY, DEFAULT_CONFIG_FILENAME)
    exclude_tags_value = _resolve_value(header, EXCLUDE_TAGS_KEY, "")
    exclude_tags = _parse_exclude_tags_value(exclude_tags_value)

    absorb_tag = _resolve_override_value(header, ABSORB_TAG_KEY)
    if absorb_tag is not None:
        absorb_tag = absorb_tag.strip()
        if not absorb_tag:
            absorb_tag = None

    llm_config = _resolve_llm_config(header)

    return DynamicsConfig(
        config_file=config_file,
        annotation_delimiter_override=annotation_delimiter_override,
        annotation_output_separator_override=output_separator_override,
        exclude_tags=exclude_tags,
        absorb_tag=absorb_tag,
        llm=llm_config,
    )


def _ceil_div(numerator: float, divisor: int) -> int:
    return int(math.ceil(numerator / divisor)) if numerator > 0 else 0


def round_seconds_to_15m_blocks(total_seconds: float) -> int:
    """Round seconds up to 15-minute blocks (900s)."""

    blocks = _ceil_div(total_seconds, 900)
    return blocks * 900


def billable_minutes_from_raw_seconds(raw_seconds: int, multiplier: float) -> int:
    """Return billable minutes by applying multiplier then rounding once per line item."""

    rounded_seconds = round_seconds_to_15m_blocks(float(raw_seconds) * float(multiplier))
    return int(rounded_seconds // 60)


def slack_seconds_from_raw_seconds(raw_seconds: int) -> int:
    """Return available slack seconds from rounding raw time to 15-minute blocks (pre-multiplier)."""

    return round_seconds_to_15m_blocks(float(raw_seconds)) - int(raw_seconds)


@dataclass
class DynamicsDraft:
    date: str
    raw_seconds: int
    multiplier: float
    tags: List[str]
    project: str
    project_task: str
    project_display: str
    project_task_display: str
    role: str
    type: str
    description: str
    external_comment: str
    annotation_delimiter: str
    output_separator: str
    llm_settings: Dict[str, Any] = field(default_factory=dict)
    absorbable: bool = False
    sequence: int = 0


def sanitize_description(
    text: str,
    input_delimiter: Optional[str],
    output_separator: str,
) -> str:
    """Remove hidden markers and join list items with the configured separator."""

    if not input_delimiter:
        return text

    parts = text.split(input_delimiter)
    visible_parts = [
        element
        for element in parts
        if not (element.startswith("++") and element.endswith("++"))
    ]
    return output_separator.join(visible_parts)


def join_unique(items: Sequence[str], delimiter: str) -> str:
    """Deduplicate list items while keeping their first-seen order."""

    unique: List[str] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return delimiter.join(unique)


def merge_annotations(existing: str, addition: str, delimiter: str) -> str:
    """Merge two delimiter-separated strings while preserving uniqueness."""

    merged = delimiter.join([existing, addition])
    return join_unique(merged.split(delimiter), delimiter)


def load_project_configuration(config_filename: str) -> List[dict]:
    """Load project definitions from the configured JSON file."""

    if os.path.isabs(config_filename):
        config_path = config_filename
    else:
        config_path = os.path.join(sys.path[0], config_filename)
    with open(config_path, encoding="utf-8") as config_file:
        return json.load(config_file)


def resolve_project_config(
    tags: Sequence[str], project_configs: Sequence[dict]
) -> dict:
    """Return the project configuration matching the provided tags."""

    tag_set = set(tags)
    chosen_config: Optional[dict] = None

    for project_config in project_configs:
        config_tags = set(project_config.get("timew_tags", []))
        if config_tags == tag_set:
            return project_config
        if config_tags < tag_set:
            if chosen_config is None:
                chosen_config = project_config
                continue
            current_tags = set(chosen_config.get("timew_tags", []))
            if len(tag_set - config_tags) < len(tag_set - current_tags):
                chosen_config = project_config

    if chosen_config:
        return chosen_config

    if tag_set:
        project_note = f"NO PROJECT FOUND FOR THESE TAGS: {', '.join(tags)}"
    else:
        project_note = "NO TAGS DEFINED TO THIS TIME ENTRY"

    return {"project": project_note, "project_task": "-", "role": "-"}


def has_excluded_tags(tags: Sequence[str], excluded_tags: set[str]) -> bool:
    if not excluded_tags or not tags:
        return False
    return any(tag in excluded_tags for tag in tags)


def build_dynamics_draft(
    timew_entry: dict,
    project_config: dict,
    config: DynamicsConfig,
    sequence: int,
) -> Tuple[DynamicsDraft, bool]:
    """Construct a DynamicsDraft from a timew record and config mapping."""

    timew_start = timew_entry["start"]
    timew_end = timew_entry["end"]

    start_dt = datetime.strptime(timew_start, TIMEW_DATETIME_FORMAT)
    end_dt = datetime.strptime(timew_end, TIMEW_DATETIME_FORMAT)

    multiplier = (
        float(project_config["multiplier"]) if "multiplier" in project_config else 1
    )
    raw_seconds = int((end_dt - start_dt).total_seconds())

    project_value = (
        project_config["project_id"]
        if "project_id" in project_config
        else project_config.get("project", "")
    )
    project_task_value = (
        project_config["project_task_id"]
        if "project_task_id" in project_config
        else project_config.get("project_task", "")
    )
    project_display = project_config.get("project", project_value)
    project_task_display = project_config.get("project_task", project_task_value)
    role_value = project_config.get("role", "")

    annotation = timew_entry.get("annotation", "")
    if config.annotation_delimiter_override is not None:
        annotation_delimiter = config.annotation_delimiter_override
    else:
        annotation_delimiter = project_config.get(
            "annotation_delimiter", DEFAULT_ANNOTATION_DELIMITER
        )
    if not annotation_delimiter:
        annotation_delimiter = DEFAULT_ANNOTATION_DELIMITER

    if config.annotation_output_separator_override is not None:
        output_separator = config.annotation_output_separator_override
    else:
        output_separator = project_config.get(
            "annotation_output_separator", DEFAULT_OUTPUT_SEPARATOR
        )
    if output_separator is None or output_separator == "":
        output_separator = DEFAULT_OUTPUT_SEPARATOR

    if "description_prefix" in project_config:
        description = (
            project_config["description_prefix"] + annotation_delimiter + annotation
        )
    else:
        description = annotation

    external_comment = project_config.get("external_comment", "")
    merge_on_equal_tags = (
        bool(project_config["merge_on_equal_tags"])
        if "merge_on_equal_tags" in project_config
        else False
    )

    entry_type = project_config.get("type", DEFAULT_TYPE)

    llm_settings: Dict[str, Any] = {}
    if "llm_enabled" in project_config:
        llm_settings["enabled"] = bool(project_config["llm_enabled"])
    if "llm_model" in project_config:
        llm_settings["model"] = project_config["llm_model"]
    if "llm_temperature" in project_config:
        try:
            llm_settings["temperature"] = float(project_config["llm_temperature"])
        except (TypeError, ValueError):
            pass
    if "llm_timeout" in project_config:
        try:
            llm_settings["timeout"] = float(project_config["llm_timeout"])
        except (TypeError, ValueError):
            pass
    if "llm_endpoint" in project_config:
        llm_settings["endpoint"] = project_config["llm_endpoint"]
    if "llm_provider" in project_config:
        llm_settings["provider"] = str(project_config["llm_provider"]).strip().lower()
    if "llm_api_key" in project_config:
        llm_settings["api_key"] = project_config["llm_api_key"]

    tags = list(timew_entry.get("tags", []) or [])
    absorbable = bool(config.absorb_tag and config.absorb_tag in tags)

    draft = DynamicsDraft(
        date=start_dt.astimezone().strftime("%Y-%m-%d"),
        raw_seconds=raw_seconds,
        multiplier=multiplier,
        tags=tags,
        project=project_value,
        project_task=project_task_value,
        project_display=project_display,
        project_task_display=project_task_display,
        role=role_value,
        type=entry_type,
        description=description,
        external_comment=external_comment,
        annotation_delimiter=annotation_delimiter,
        output_separator=output_separator,
        llm_settings=llm_settings,
        absorbable=absorbable,
        sequence=sequence,
    )

    return draft, merge_on_equal_tags


def finalize_draft(draft: DynamicsDraft) -> DynamicsRecord:
    return DynamicsRecord(
        date=draft.date,
        duration_minutes=billable_minutes_from_raw_seconds(
            draft.raw_seconds, draft.multiplier
        ),
        project=draft.project,
        project_task=draft.project_task,
        project_display=draft.project_display,
        project_task_display=draft.project_task_display,
        role=draft.role,
        type=draft.type,
        description=draft.description,
        external_comment=draft.external_comment,
        annotation_delimiter=draft.annotation_delimiter,
        output_separator=draft.output_separator,
        llm_settings=draft.llm_settings,
    )


def build_dynamics_records(
    timew_entries: Sequence[dict],
    project_configs: Sequence[dict],
    config: DynamicsConfig,
    merge_on_display_values: bool,
    include_format_in_merge: bool,
) -> List[DynamicsRecord]:
    records, _report = build_dynamics_records_with_absorption_report(
        timew_entries,
        project_configs,
        config,
        merge_on_display_values=merge_on_display_values,
        include_format_in_merge=include_format_in_merge,
    )
    return records


def build_dynamics_records_with_absorption_report(
    timew_entries: Sequence[dict],
    project_configs: Sequence[dict],
    config: DynamicsConfig,
    merge_on_display_values: bool,
    include_format_in_merge: bool,
) -> Tuple[List[DynamicsRecord], List[AbsorptionDayReport]]:
    drafts: List[DynamicsDraft] = []
    sequence = 0

    for timew_entry in timew_entries:
        if "end" not in timew_entry:
            continue

        tags = timew_entry.get("tags", [])
        if has_excluded_tags(tags, config.exclude_tags):
            continue

        project_config = resolve_project_config(tags, project_configs)
        draft, merge_on_equal_tags = build_dynamics_draft(
            timew_entry,
            project_config,
            config,
            sequence=sequence,
        )
        sequence += 1
        merge_drafts(
            drafts,
            draft,
            merge_on_equal_tags,
            merge_on_display_values=merge_on_display_values,
            include_format_in_merge=include_format_in_merge,
        )

    absorption_report: List[AbsorptionDayReport] = []
    if config.absorb_tag:
        drafts, absorption_report = apply_absorption(drafts, config.absorb_tag)

    records = [finalize_draft(draft) for draft in drafts]
    return records, absorption_report


def apply_absorption(
    drafts: Sequence[DynamicsDraft], absorb_tag: str
) -> Tuple[List[DynamicsDraft], List[AbsorptionDayReport]]:
    """Reduce absorb-tag drafts by consuming same-day slack from non-absorb drafts."""

    by_day: Dict[str, List[DynamicsDraft]] = {}
    for draft in drafts:
        by_day.setdefault(draft.date, []).append(draft)

    updated: List[DynamicsDraft] = []
    reports: List[AbsorptionDayReport] = []

    for day in sorted(by_day.keys()):
        day_drafts = list(sorted(by_day[day], key=lambda item: item.sequence))
        admin = [item for item in day_drafts if item.absorbable and absorb_tag in item.tags]
        work = [item for item in day_drafts if not (item.absorbable and absorb_tag in item.tags)]

        if not admin:
            updated.extend(day_drafts)
            continue

        slack_seconds = sum(slack_seconds_from_raw_seconds(item.raw_seconds) for item in work)
        admin_raw_seconds = sum(item.raw_seconds for item in admin)

        slack_remaining = slack_seconds
        absorbed_seconds = 0

        for item in admin:
            if slack_remaining <= 0:
                break
            reduce_by = min(item.raw_seconds, slack_remaining)
            item.raw_seconds -= reduce_by
            slack_remaining -= reduce_by
            absorbed_seconds += reduce_by

        admin_left = [item for item in admin if item.raw_seconds > 0]
        leftover_raw_seconds = sum(item.raw_seconds for item in admin_left)
        leftover_exported_minutes = sum(
            billable_minutes_from_raw_seconds(item.raw_seconds, item.multiplier)
            for item in admin_left
        )

        reports.append(
            AbsorptionDayReport(
                date=day,
                slack_seconds=slack_seconds,
                admin_raw_seconds=admin_raw_seconds,
                absorbed_seconds=absorbed_seconds,
                leftover_raw_seconds=leftover_raw_seconds,
                leftover_exported_minutes=leftover_exported_minutes,
            )
        )

        updated.extend(work)
        updated.extend(admin_left)

    updated.sort(key=lambda item: item.sequence)
    return updated, reports


def merge_drafts(
    drafts: List[DynamicsDraft],
    new_draft: DynamicsDraft,
    merge_on_equal_tags: bool,
    merge_on_display_values: bool,
    include_format_in_merge: bool,
) -> None:
    """Merge the new draft into the list when a matching slot exists."""

    for existing in drafts:
        if not should_merge_base_draft(
            existing,
            new_draft,
            merge_on_display_values=merge_on_display_values,
            include_format_in_merge=include_format_in_merge,
        ):
            continue

        delimiter = existing.annotation_delimiter

        if existing.description == new_draft.description:
            existing.raw_seconds += new_draft.raw_seconds
            return

        if (
            merge_on_equal_tags
            and len(existing.description) + len(new_draft.description)
            <= MAX_DESCRIPTION_LENGTH
        ):
            existing.raw_seconds += new_draft.raw_seconds
            existing.description = merge_annotations(
                existing.description, new_draft.description, delimiter
            )
            return

        existing_title = existing.description.split(delimiter)[0]
        new_title = new_draft.description.split(delimiter)[0]

        if (
            existing_title == new_title
            and len(existing.description) + len(new_draft.description)
            <= MAX_DESCRIPTION_LENGTH
        ):
            existing.raw_seconds += new_draft.raw_seconds
            note_items_without_title = delimiter.join(
                new_draft.description.split(delimiter)[1:]
            )
            existing.description = merge_annotations(
                existing.description, note_items_without_title, delimiter
            )
            return

    drafts.append(new_draft)


def should_merge_base_draft(
    existing: DynamicsDraft,
    new_draft: DynamicsDraft,
    merge_on_display_values: bool,
    include_format_in_merge: bool,
) -> bool:
    project_value = (
        existing.project_display if merge_on_display_values else existing.project
    )
    project_task_value = (
        existing.project_task_display
        if merge_on_display_values
        else existing.project_task
    )
    new_project_value = (
        new_draft.project_display if merge_on_display_values else new_draft.project
    )
    new_project_task_value = (
        new_draft.project_task_display
        if merge_on_display_values
        else new_draft.project_task
    )

    if (
        existing.date != new_draft.date
        or project_value != new_project_value
        or project_task_value != new_project_task_value
        or existing.role != new_draft.role
        or existing.type != new_draft.type
        or existing.multiplier != new_draft.multiplier
        or existing.absorbable != new_draft.absorbable
    ):
        return False

    if include_format_in_merge:
        return (
            existing.annotation_delimiter == new_draft.annotation_delimiter
            and existing.output_separator == new_draft.output_separator
        )

    return True


def _resolve_value(header: Dict[str, str], key: str, default: str) -> str:
    value = default
    header_value = _get_header_value(header, key)
    if header_value is not None:
        value = header_value
    env_value = _get_env_value(key)
    if env_value is not None:
        value = env_value
    return value


def _resolve_override_value(header: Dict[str, str], key: str) -> Optional[str]:
    env_value = _get_env_value(key)
    if env_value is not None:
        return env_value
    header_value = _get_header_value(header, key)
    if header_value is not None:
        return header_value
    return None


def _get_header_value(header: Dict[str, str], key: str) -> Optional[str]:
    if key not in header:
        return None
    return header.get(key, "").strip()


def _get_env_value(key: str) -> Optional[str]:
    env_key = _env_key_for_header(key)
    raw = os.getenv(env_key)
    if raw is None:
        return None
    return raw.strip()


def _env_key_for_header(header_key: str) -> str:
    return "TIMEWARRIOR_" + header_key.upper().replace(".", "_")


def _parse_exclude_tags_value(raw: Optional[str]) -> set[str]:
    if not raw:
        return set()
    return {tag.strip() for tag in raw.split(",") if tag.strip()}


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lower = value.strip().lower()
    if lower in {"1", "true", "yes", "on"}:
        return True
    if lower in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _resolve_llm_config(header: Dict[str, str]) -> LLMConfig:
    enabled_raw = _resolve_value(header, LLM_ENABLED_KEY, "false")
    enabled = _parse_bool(enabled_raw)
    enabled_value = enabled if enabled is not None else False

    provider_raw = _resolve_value(header, LLM_PROVIDER_KEY, "ollama")
    provider = provider_raw.strip().lower() if provider_raw else "ollama"
    if provider not in {"ollama", "openai"}:
        provider = "ollama"

    endpoint_raw = _resolve_value(header, LLM_ENDPOINT_KEY, "")
    model_raw = _resolve_value(header, LLM_MODEL_KEY, "")

    if provider == "openai":
        endpoint = endpoint_raw or DEFAULT_OPENAI_ENDPOINT
        model = model_raw or DEFAULT_OPENAI_MODEL
    else:
        endpoint = endpoint_raw or DEFAULT_LLM_ENDPOINT
        model = model_raw or DEFAULT_LLM_MODEL

    temperature_raw = _resolve_value(
        header, LLM_TEMPERATURE_KEY, str(DEFAULT_LLM_TEMPERATURE)
    )
    timeout_raw = _resolve_value(header, LLM_TIMEOUT_KEY, str(DEFAULT_LLM_TIMEOUT))
    temperature = _parse_float(temperature_raw, DEFAULT_LLM_TEMPERATURE)
    timeout = _parse_float(timeout_raw, DEFAULT_LLM_TIMEOUT)

    api_key = _resolve_value(header, LLM_OPENAI_API_KEY_KEY, "")
    api_key_value = api_key or None

    return LLMConfig(
        enabled=enabled_value,
        provider=provider,
        endpoint=endpoint,
        model=model,
        temperature=temperature,
        timeout=timeout,
        api_key=api_key_value,
    )
