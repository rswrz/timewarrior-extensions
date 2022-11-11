#!/usr/bin/env python3

import json
import sys

# Skip the configuration settings.
for line in sys.stdin:
    if line == '\n':
        break

# Extract the JSON.
doc = ''
for line in sys.stdin:
    doc += line

total_active_time = 0

j = json.loads(doc)

delimiter = ','
head_line= delimiter.join(["Start","End","Annotation","Tags"])
print(head_line)

for object in j:
    line = '"{}","{}"'.format(object['start'], (object['end'] if 'end' in object else ''))
    line += ',"{}"'.format(object['annotation'] if 'annotation' in object else '')
    line += ',"{}"'.format(' '.join(object['tags'] if 'tags' in object else []))
    print(line)
