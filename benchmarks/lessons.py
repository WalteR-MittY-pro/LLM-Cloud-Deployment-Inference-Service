"""把每天的练习函数接到一条调用链；切换实现不会改动任何文件。"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lesson(day, impl, name="exercise"):
    path = ROOT / "course" / f"day-{day:02}" / impl / f"{name}.py"
    spec = spec_from_file_location(f"day{day}_{impl}_{name}", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
