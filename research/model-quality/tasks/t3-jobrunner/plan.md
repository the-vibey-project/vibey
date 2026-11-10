The repository in the current directory runs batches of work under a lock (lock.py, runner.py). One test
fails: tests/test_runner.py::test_the_lock_is_free_after_a_stopped_batch. Run it with
`python -m pytest -q tests/test_runner.py`.

Symptom: after a batch that contains a None item, the next call to process() fails with
RuntimeError("lock already held"), and the lock stays stuck for the rest of the program.

The rule the code is meant to follow: process(batch, lock, handler) takes the lock, calls handler on each
item in order, and returns how many items were handled. A None item ends the batch early: the items before
it are handled, the rest are skipped. Whatever happens, the lock is released before process() returns or
lets an exception escape. If the handler raises, the exception propagates to the caller unchanged and the
count of items handled so far is lost.

Find the root cause in runner.py and fix it there. Do not edit anything under tests/. Run the whole tests/
folder, then finish.
