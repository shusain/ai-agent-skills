"""CLI path handling shared by concrete plan/Blender/report consumers.

Resolves skill assets independently of cwd; generated runs belong outside the
skill source tree. Does not create directories or start applications.
"""
from pathlib import Path
import sys
from . import RESOURCE_ROOT

def output_path(value):
    path=Path(value).expanduser().resolve()
    if path.is_relative_to(RESOURCE_ROOT):
        raise ValueError('Write generated runs outside the skill source directory')
    return path

def blender_argv():
    return sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]

def example_svg():
    return RESOURCE_ROOT/'assets'/'examples'/'family-wing.svg'
