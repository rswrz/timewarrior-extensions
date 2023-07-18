#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timedelta, timezone

# Skip the configuration settings.
for line in sys.stdin:
    if line == '\n':
        break

# Extract the JSON.
doc = ''
for line in sys.stdin:
    doc += line

total_active_time = 0

layout = "{:<2} {:<10} {:<3} {:<4} {:<60} {:<80} {:<9} {:<9} {:<9}"
layout_head = "\033[4m" + "\033[0m \033[4m".join(layout.split(" ")) + "\033[0m"

print (layout_head.format('Wk', 'Date', 'Day', 'ID','Tags','Annotation','Start','End','Time'))

j = json.loads(doc)
prev = {}
for object in j:

    date_format = "%Y%m%dT%H%M%S%z"
    start_date = datetime.strptime(object["start"], date_format)
    end_date = datetime.strptime(object["end"], date_format) if "end" in object else None

    _week = start_date.isocalendar().week
    week = _week if "start" not in prev or ("start" in prev and _week != datetime.strptime(prev["start"], date_format).isocalendar().week) else ""

    _date = start_date.strftime("%Y-%m-%d")
    date = _date if "start" not in prev or ("start" in prev and _date != datetime.strptime(prev["start"], date_format).strftime("%Y-%m-%d")) else ""

    _day = start_date.strftime("%a")
    day = _day if "start" not in prev or ("start" in prev and _day != datetime.strptime(prev["start"], date_format).strftime("%a")) else ""

    id = "@" + str(object["id"])

    tags_list = object["tags"] if "tags" in object else []
    tags = ", ".join(f"{tag}" for tag in tags_list)

    annotation = object["annotation"].replace(";", "\n") if "annotation" in object else ""

    start = start_date.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S")
    end = end_date.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S") if end_date else " "
    time = str(timedelta(seconds=(end_date - start_date).total_seconds())) if end_date else " "

    for i, value in enumerate(annotation.split("\n")):
        if i == 0:
            print (layout.format(week, date, day, id, tags, value, start, end, time))
        else:
            s = ' '
            print (s*82, value)
    
    prev = object

