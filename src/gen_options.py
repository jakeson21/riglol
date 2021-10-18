#!/usr/bin/env python

import json, sys

devices = json.load(open("options.json"))

option_template = '	{{ .code = "{code}", .description = "{description}" }},'
options_template = """
static struct riglol_device_option riglol_device_options_{device[name]}[] = {{
{options}
}};
"""
device_template = """
static struct riglol_device riglol_device_{name} = {{
	.name = "{name}",
	.description = "{description}",
	.notes = "{notes}",
	
	.num_options = {num_options},
	.options = {options},
}};
"""
devices_template = """
static struct riglol_device *riglol_devices[] = {{
{devices}
}};
"""

with sys.stdout as of:
	of.write(open('options.h.in').read())
	for device in devices:
		options = "\n".join([ option_template.format(code=k, description=v) for k, v in device['options'] ])
		of.write(options_template.format(device=device, options=options))
		num_options = len(device['options'])
		options = f"&riglol_device_options_{device['name']}"
		of.write(device_template.format(name=device['name'], description=device['description'], notes=device['notes'], num_options=num_options, options=options))
	devices = "\n".join([ f"&riglol_device_{device['name']}," for device in devices ])
	of.write(devices_template.format(devices=devices))
