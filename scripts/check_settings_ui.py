#!/usr/bin/env python3
"""Standalone webview/Swift Settings source integrity gate v1.0.0."""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('settings_ui_manifest.json'));args=parser.parse_args()
manifest=args.manifest.resolve();root=manifest.parent.parent;data=json.loads(manifest.read_text())
if data['version']!='1.0.0':raise SystemExit('Unsupported Settings adapter version')
for name,expected in data['files'].items():
 path=(root/name).resolve()
 if not path.is_relative_to(root):raise SystemExit('Invalid manifest path')
 if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise SystemExit('Settings adapter drift: '+name+'; update canonical source and sync')
print('Settings adapter '+data['version']+': integrity PASS')
