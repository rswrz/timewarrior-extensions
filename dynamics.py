#!/usr/bin/env python3

from datetime import datetime, timedelta
import json
import math
import sys
import os

# import ollama


def calculate_working_time(datetime_start: datetime, datetime_end: datetime, multiplier=1):
    datetime_delta = datetime_end - datetime_start
    total_seconds = datetime_delta.total_seconds()
    total_seconds_multiplied = total_seconds * multiplier

    total_minutes_rounded_15m = math.ceil(round(total_seconds_multiplied / 60) / 15) * 15

    return total_minutes_rounded_15m


def csv_escape_special_chars(text):
    escaped_text = text.replace('"', '""').replace("\\", "\\\\")
    return escaped_text


def get_project_and_task(tags):
    # Open project config file
    dynamics_config_json = os.getenv("TIMEWARRIOR_EXT_DYNAMICS_CONFIG_JSON", ".dynamics_config.json")
    f = open(os.path.join(sys.path[0], dynamics_config_json))
    project_identifier = json.load(f)

    # Get the project with the most matching tags
    project = None
    for pi in project_identifier:
        stags = set(tags)
        spitags = set(pi["timew_tags"])
        if spitags == stags:
            return pi
        if spitags < stags:
            if project:
                project_current = set(project["timew_tags"])
                if len(stags - spitags) < len(stags - project_current):
                    project = pi
                continue
            else:
                project = pi
                continue

    # Project not found, fallback
    if not project:
        if len(tags) == 0:
            _no_project_note = "NO TAGS DEFINED TO THIS TIME ENTRY"
        else:
            _no_project_note = "NO PROJECT FOUND FOR THESE TAGS: {}".format(", ".join(tags))
        project = {"project": _no_project_note, "project_task": "-", "role": "-"}

    return project


def print_line(list, annotation_delimiter=None, end=None):
    csv_column_delimiter = ","
    list[6] = ";\n".join(
        [
            element
            for element in list[6].split(annotation_delimiter)
            if not (element.startswith("++") and element.endswith("++"))
        ]
    )
    line = csv_column_delimiter.join(f'"{csv_escape_special_chars(item)}"' for item in list)
    print(line, end=end)


# def improve_description_with_ai(description):
#     response = ollama.chat(
#         model="mistral",
#         options={
#             "temperature": 0
#         },
#         messages=[
#             {
#                 "role": "system",
#                 "content": """
#                     You are an AI language model designed to process time-tracking entries provided by the user. The user will input one or more time-tracking entries, separated by “; “. Your task is to correct any spelling or grammatical errors while preserving the original meaning.

#                     Instruction:
#                     - Accept a text input that contains one or more time-tracking entries separated by “; “.
#                     - Correct any spelling, punctuation, and grammatical mistakes while keeping the structure intact.
#                     - Do not change the meaning of the entries.
#                     - Maintain the original format, ensuring that multiple entries remain separated by “; “.
#                     - Preserve any user handles that start with “@” without modification.
#                     - Preserve any GitHub issue references starting with a "#" or “repository/#” without modification.
#                     - Do not add, remove, or reorder information.
#                     - Respond only with the corrected text and no additional explanations.
#                 """,
#             },
#             {
#                 "role": "user",
#                 "content": description,
#             },
#         ],
#     )

#     return response["message"]["content"]


def format_description_as_title_with_list_items(description, delimiter):
    _description_list = description.split(delimiter)
    title = _description_list.pop(0)

    if len(_description_list) == 0:
        return title
    elif len(_description_list) >= 1:
        list_items = "\n - ".join(_description_list)
        return "{}\n - {}".format(title, list_items)


if __name__ == "__main__":
    #
    # stdin
    #

    # Skip the configuration settings
    for line in sys.stdin:
        if line == "\n":
            break

    # Extract the JSON.
    tmp = ""
    for line in sys.stdin:
        tmp += line
    timew_export = json.loads(tmp)
    del tmp

    #
    # process
    #

    dynamics_max_description_length = 500
    dynamics_time_entries = []
    timew_annotation_delimiter = "; "
    for _timew_entry in timew_export:
        # Skip if time _timew_entry entry has not ended yet
        if "end" not in _timew_entry:
            continue

        #
        # Timewarrior data
        #

        # Fields exported by `timew export` command
        timew_id = _timew_entry["id"]
        timew_start = _timew_entry["start"]
        timew_end = _timew_entry["end"]
        timew_tags = _timew_entry["tags"] if "tags" in _timew_entry else []
        timew_annotation = _timew_entry["annotation"] if "annotation" in _timew_entry else ""

        _timew_datetime_format = "%Y%m%dT%H%M%S%z"
        _datetime_timew_start = datetime.strptime(timew_start, _timew_datetime_format)
        _datetime_timew_end = datetime.strptime(timew_end, _timew_datetime_format)

        #
        # Project data from configuration file
        #

        # Get projects project which matches the timewarrior entry tags
        _project = get_project_and_task(timew_tags)

        # Get the project id or name from the configuration file
        project = (
            _project["project_id"] if "project_id" in _project else _project["project"] if "project" in _project else ""
        )

        # Get the project task id or name from the configuration file
        project_task = (
            _project["project_task_id"]
            if "project_task_id" in _project
            else _project["project_task"]
            if "project_task" in _project
            else ""
        )

        # Get the project role from the configuration file
        project_role = _project["role"] if "role" in _project else ""

        # Get the time multiplier from configuration file, fallback to 1
        multiplier = float(_project["multiplier"]) if "multiplier" in _project else 1

        merge_on_equal_tags = bool(_project["merge_on_equal_tags"]) if "merge_on_equal_tags" in _project else False

        #
        # Time Entry values
        #

        # DATE
        # Calculate the date based on the timewarrior start time
        time_entry_date = _datetime_timew_start.astimezone().strftime("%Y-%m-%d")

        # DURATION
        # Calculate the time entry duration
        time_entry_duration = calculate_working_time(_datetime_timew_start, _datetime_timew_end, multiplier)

        # TYPE
        time_entry_type = "Work"

        # PROJECT
        time_entry_project = project

        # PROJECT TASK
        time_entry_project_task = project_task

        # ROLE
        time_entry_role = project_role

        # DESCRIPTION
        # Set the time entry description from the timewarrior annotation
        # and optionally prefixed with a value from the configuration file
        if "description_prefix" in _project:
            time_entry_description = _project["description_prefix"] + timew_annotation_delimiter + timew_annotation
        else:
            time_entry_description = timew_annotation

        # time_entry_description = improve_description_with_ai(time_entry_description)

        # EXTERNAL COMMENT
        # set the external comment to a value from the configuration file, if any
        if "external_comment" in _project:
            time_entry_external_comment = _project["external_comment"]
        else:
            time_entry_external_comment = ""

        #
        # Transform timewarrior tracks zu time entries
        #

        for i, dynamics_time_entry in enumerate(dynamics_time_entries):
            (
                _date,
                _duration,
                _project,
                _project_task,
                _role,
                _type,
                _description,
                _external_comments,
            ) = tuple(dynamics_time_entry)

            # If there is already an time entry with the same data, add duration up
            if (
                _date == time_entry_date
                and _project == time_entry_project
                and _project_task == time_entry_project_task
                and _role == time_entry_role
                and _type == time_entry_type
                and _description == time_entry_description
            ):
                # Add up duration
                _time_entry_duration_added_up = int(_duration) + time_entry_duration

                # Overwrite existing entry with new duration
                dynamics_time_entries[i] = [
                    time_entry_date,
                    str(_time_entry_duration_added_up),
                    time_entry_project,
                    time_entry_project_task,
                    time_entry_role,
                    time_entry_type,
                    time_entry_description,
                    time_entry_external_comment,
                ]
                break

            # Merge on same first line – merge_on_equal_tags=True

            elif (
                _date == time_entry_date
                and _project == time_entry_project
                and _project_task == time_entry_project_task
                and _role == time_entry_role
                and _type == time_entry_type
                and merge_on_equal_tags
                and len(_description) + len(time_entry_description) <= dynamics_max_description_length
            ):
                _time_entry_duration_added_up = int(_duration) + time_entry_duration

                _merged_notes = timew_annotation_delimiter.join([_description, time_entry_description])
                _uniq_merged_notes = []
                for n in _merged_notes.split(timew_annotation_delimiter):
                    if n not in _uniq_merged_notes:
                        _uniq_merged_notes.append(n)
                _uniq_merged_notes_string = timew_annotation_delimiter.join(_uniq_merged_notes)

                dynamics_time_entries[i] = [
                    time_entry_date,
                    str(_time_entry_duration_added_up),
                    time_entry_project,
                    time_entry_project_task,
                    time_entry_role,
                    time_entry_type,
                    _uniq_merged_notes_string,
                    time_entry_external_comment,
                ]
                break

            # Merge on same first line

            elif (
                _date == time_entry_date
                and _project == time_entry_project
                and _project_task == time_entry_project_task
                and _role == time_entry_role
                and _type == time_entry_type
                and _description.split(timew_annotation_delimiter)[0]
                == time_entry_description.split(timew_annotation_delimiter)[0]
                and len(_description) + len(time_entry_description) <= dynamics_max_description_length
            ):
                _time_entry_duration_added_up = int(_duration) + time_entry_duration

                note_items_without_title = timew_annotation_delimiter.join(
                    time_entry_description.split(timew_annotation_delimiter)[1:]
                )
                _merged_notes = timew_annotation_delimiter.join([_description, note_items_without_title])
                _uniq_merged_notes = []
                for n in _merged_notes.split(timew_annotation_delimiter):
                    if n not in _uniq_merged_notes:
                        _uniq_merged_notes.append(n)
                _uniq_merged_notes_string = timew_annotation_delimiter.join(_uniq_merged_notes)

                dynamics_time_entries[i] = [
                    time_entry_date,
                    str(_time_entry_duration_added_up),
                    time_entry_project,
                    time_entry_project_task,
                    time_entry_role,
                    time_entry_type,
                    _uniq_merged_notes_string,
                    time_entry_external_comment,
                ]
                break

        #
        # Add time entry
        #

        else:
            dynamics_time_entries.append(
                [
                    time_entry_date,
                    str(time_entry_duration),
                    time_entry_project,
                    time_entry_project_task,
                    time_entry_role,
                    time_entry_type,
                    time_entry_description,
                    time_entry_external_comment,
                ]
            )

    #
    # stdout
    #

    print_line(
        [
            "Date",
            "Duration",
            "Project",
            "Project Task",
            "Role",
            "Type",
            "Description",
            "External Comments",
        ]
    )
    for i, dynamics_time_entry in enumerate(dynamics_time_entries):
        end = None
        if i + 1 == len(dynamics_time_entries):
            end = ""
        print_line(dynamics_time_entry, timew_annotation_delimiter, end=end)
