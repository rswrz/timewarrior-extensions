#!/usr/bin/env python3

from datetime import datetime, timedelta
import json
import math
import sys
import os


def calculate_working_time(
    datetime_start: datetime, datetime_end: datetime, multiplier=1
):
    datetime_delta = datetime_end - datetime_start
    total_seconds = datetime_delta.total_seconds()
    total_seconds_multiplied = total_seconds * multiplier

    total_minutes_rounded_15m = (
        math.ceil(round(total_seconds_multiplied / 60) / 15) * 15
    )
    result = timedelta(minutes=total_minutes_rounded_15m)

    return result


def csv_escape_special_chars(text):
    escaped_text = text.replace('"', '""').replace("\\", "\\\\")
    return escaped_text


def get_project_and_task(tags):

    # Open project config file
    f = open(os.path.join(sys.path[0], ".zoho_config.json"))
    project_identifier = json.load(f)

    # Get the project with the most matching tags
    project = None
    for pi in project_identifier:
        stags = set(tags)
        spitags = set(pi["tag"])
        if spitags == stags:
            return pi
        if spitags < stags:
            if project:
                project_current = set(project["tag"])
                if len(stags - spitags) < len(stags - project_current):
                    project = pi
                continue
            else:
                project = pi
                continue

    # Project not found, fallback
    if not project:
        project = {
            "project_name": "NO PROJECT FOUND FOR THESE TAGS: {}".format(
                ", ".join(tags)
            ),
            "task_name": "",
        }

    return project


def print_line(list):
    delimiter = ","
    line = delimiter.join(f'"{csv_escape_special_chars(item)}"' for item in list)
    print(line)


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
    json_doc = json.loads(tmp)
    del tmp

    #
    # process
    #

    data = []
    for track in json_doc:

        # Skip if time track entry has not ended yet
        if "end" not in track:
            continue

        # Join tags to a comma separated string
        tags = track["tags"] if "tags" in track else []
        tags_list = ", ".join(f"{t}" for t in tags)

        # Annotations as notes
        notes = track["annotation"] if "annotation" in track else ""

        # Get Zoho project and task named based on tags
        project = get_project_and_task(tags)
        project_name = project["project_name"]
        task_name = project["task_name"]
        billable_status = "Billable" if project.get("billable") == True else "Non Billable"
        multiplier = float(project["multiplier"]) if "multiplier" in project else 1

        # start, end, worktime
        timew_datetime_format = "%Y%m%dT%H%M%S%z"
        start = datetime.strptime(track["start"], timew_datetime_format)
        end = datetime.strptime(track["end"], timew_datetime_format)
        time_spend = calculate_working_time(start, end, multiplier)

        date_string = start.astimezone().strftime("%Y-%m-%d")
        # start_string = start.astimezone().strftime('%H:%M:%S')
        # end_string = start.astimezone().strftime('%H:%M:%S')
        time_spend_string = str(time_spend)[:-3]

        for i, d in enumerate(data):
            # print("-->", d[0], d[2], d[3], d[4])
            if (
                d[0] == date_string
                and d[2] == project_name
                and d[3] == task_name
                and d[4] == notes
            ):
                t = datetime.strptime(d[1], "%H:%M")
                d = timedelta(hours=t.hour, minutes=t.minute)
                d_new = d + time_spend
                d_new_string = str(d_new)[:-3]
                data[i] = [date_string, d_new_string, project_name, task_name, billable_status, notes]
                break
        else:
            data.append(
                [date_string, time_spend_string, project_name, task_name, billable_status, notes]
            )

    #
    # stdout
    #

    print_line(["Date", "Time Spent", "Project Name", "Task Name", "Billable Status", "Notes"])
    for d in data:
        print_line(d)
