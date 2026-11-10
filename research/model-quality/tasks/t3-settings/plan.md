The repository in the current directory loads application settings (settings.py) and prints a summary
(report.py). One test fails: tests/test_settings.py::test_an_override_does_not_leak_into_later_loads.
Run it with `python -m pytest -q tests/test_settings.py`.

Symptom: after one call to load_settings({"editor": {"tabs": 2}}), every later call to load_settings(),
even with no arguments, reports tabs as 2 instead of the default 4.

The rule the code is meant to follow: DEFAULTS is a constant that is never changed. Every call to
load_settings returns a fresh, independent dictionary: the defaults, with any top-level override replacing
the default, except that when both the default and the override are dictionaries their keys are combined
(override keys win). Changing a returned dictionary, including its nested dictionaries and lists, must not
affect DEFAULTS or the result of any later call.

Find the root cause in settings.py and fix it there. Do not edit anything under tests/. Run the whole
tests/ folder, then finish.
