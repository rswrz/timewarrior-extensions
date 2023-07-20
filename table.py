#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timedelta, timezone, time

# Save the configuration settings.
conf = {}
for line in sys.stdin:
    if line == '\n':
        break
    l_split = line.split(": ")
    key = l_split[0]
    value = ": ".join(l_split[1:]).replace('\n', '')
    conf[key] = value

# Extract the JSON.
doc = ''
for line in sys.stdin:
    doc += line
j = json.loads(doc)

max_tags_len = len("Tags")
max_id_len = len("ID")
max_annotation_len = len("Annotation")

for object in j:
    tags_list = object["tags"] if "tags" in object else []
    tags = ", ".join(f"{tag}" for tag in tags_list)
    tags_len = len(tags)
    max_tags_len = tags_len if tags_len > max_tags_len else max_tags_len

    id = "@" + str(object["id"])
    id_len = len(id)
    max_id_len = id_len if id_len > max_id_len else max_id_len

    annotation = object["annotation"].replace(";", "\n") if "annotation" in object else ""
    for i, value in enumerate(annotation.split("\n")):
        annotation_len = len(value.strip())
        if i > 0: annotation_len += 2
        if annotation_len > max_annotation_len: max_annotation_len = annotation_len
        if annotation_len > 100: max_annotation_len = 100

layout = f"{{:<3}} {{:<10}} {{:<3}} {{:<{max_id_len}}} {{:<{max_tags_len}}} {{:<{max_annotation_len}}} {{:>8}} {{:>8}} {{:>8}} {{:>8}}"
layout_head = "\033[4m" + "\033[0m \033[4m".join(layout.split(" ")) + "\033[0m"

print (layout_head.format('Wk', 'Date', 'Day', 'ID','Tags','Annotation','Start','End','Time', 'Total'))

prev = {}
total_day = timedelta()
total_all = timedelta()

for i, object in enumerate(j):
    date_format = "%Y%m%dT%H%M%S%z"
    start_date = datetime.strptime(object["start"], date_format)
    end_date = datetime.strptime(object["end"], date_format) if "end" in object else None

    _date = start_date.strftime("%Y-%m-%d")
    date = _date if "start" not in prev or ("start" in prev and _date != datetime.strptime(prev["start"], date_format).strftime("%Y-%m-%d")) else ""

    _week = start_date.isocalendar().week
    week = "W" + str(_week) if "start" not in prev or ("start" in prev and _date != datetime.strptime(prev["start"], date_format).strftime("%Y-%m-%d")) else ""

    _day = start_date.strftime("%a")
    day = _day if "start" not in prev or ("start" in prev and _day != datetime.strptime(prev["start"], date_format).strftime("%a")) else ""

    id = "@" + str(object["id"])

    tags_list = object["tags"] if "tags" in object else []
    tags = ", ".join(f"{tag}" for tag in tags_list)

    start = start_date.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S")
    end = end_date.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S") if end_date else "-"
    _time = timedelta(seconds=(end_date - start_date).total_seconds()) if end_date else timedelta(seconds=(datetime.now(tz=timezone.utc).replace(microsecond=0) - start_date).total_seconds())
    time = str(_time)

    nxt = i + 1
    prv = i - 1
    if prv > 0 and prv <= len(j) and datetime.strptime(j[prv]["start"], date_format).date() < start_date.date():
        total_day = timedelta()
    total_day += _time

    total_all += _time

    total = str(total_day) if (nxt > 0 and nxt < len(j) and datetime.strptime(j[nxt]["start"], date_format).date() > start_date.date()) or i+1 == len(j) else " "
    
    _annotation = object["annotation"].replace("; ", "\n") if "annotation" in object else "-"

    _annotation_split_newline = _annotation.split("\n")
    max_len=100
    for a in _annotation_split_newline:
        if len(a) > max_len:
            pos = _annotation_split_newline.index(a)
            temp = [a[i:i+max_len] for i in range(0, len(a), max_len)]
            _annotation_split_newline[pos:pos+1] = [temp[0]] + ["  " + t for i,t in enumerate(temp) if i > 0]

    for ii, value in enumerate(_annotation_split_newline):
        annotation = value
        if ii == 0:
            if annotation == "-": print('\033[38;2;238;162;87m', end="")
            if i % 2 != 0: print('\033[48;2;26;26;26m', end="")
            print (layout.format(week, date, day, id, tags, annotation, start, end, time, total), end="")
            if i % 2 != 0 or annotation == "-": print("\033[0m")
            else: print("")
        else:
            if i % 2 != 0: print('\033[48;2;26;26;26m', end="")
            spaces = (3+1) + (10+1) + (3+1) + (max_id_len + 1) + (max_tags_len + 1) + 2
            print (layout.format(" ", " ", " ", " ", " ", annotation, " ", " ", " ", " "), end="")
            if i % 2 != 0: print("\033[0m")
            else: print("")
    
    if nxt > 0 and nxt < len(j) and "end" in object and object["end"] != j[nxt]["start"] and datetime.strptime(j[nxt]["start"], date_format).date() <= start_date.date() and datetime.strptime(j[nxt]["start"], date_format).replace(tzinfo=timezone.utc).astimezone(tz=None).time() < datetime.strptime(j[nxt]["start"], date_format).replace(hour=14,minute=0,tzinfo=timezone.utc).astimezone(tz=None).time():
        # print('\033[48;2;7;12;82m', end="")
        print('\033[38;2;85;85;85m', end="")
        print (layout.format(" ", " ", " ", "-", "-", "-", end, datetime.strptime(j[nxt]["start"], date_format).replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S"), str(timedelta(seconds=(datetime.strptime(j[nxt]["start"], date_format) - end_date).total_seconds())), " "), end="")
        print("\033[0m")
    

    prev = object


def format_timedelta(td):
    minutes, seconds = divmod(td.seconds + td.days * 86400, 60)
    hours, minutes = divmod(minutes, 60)
    return '{:d}:{:02d}:{:02d}'.format(hours, minutes, seconds)

spaces = (3 + 1) + (10 + 1) + (3 + 1) + (max_id_len + 1) + (max_tags_len + 1) + (max_annotation_len + 1) + (8 + 1) + (8 + 1) + (8 + 1) + (8)
total_all_str = format_timedelta(total_all)
underline_start = "\033[4m"
underline_end = "\033[0m"
print(f"{{:>{spaces + len(underline_start)}}}".format(underline_start + (len(total_all_str) * ' ')) + underline_end)
print(f"{{:>{spaces}}}".format(total_all_str))
