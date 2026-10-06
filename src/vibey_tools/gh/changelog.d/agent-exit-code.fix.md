* **pr-review:** the open-weights repair step records the agent's exit code even when it is
  nonzero. The runner's shell is `bash -e`, so the step used to end before `code=$?` ran,
  and the hand-over could only say that the agent "did not exit 0".
