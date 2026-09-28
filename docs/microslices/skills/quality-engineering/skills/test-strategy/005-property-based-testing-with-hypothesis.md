---
id: skill-property-based-testing-with-hypothesis-00be087fe4
purpose: property based testing with hypothesis
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-consumer-driven-contract-testing-bf5fe2b3f9"]
links: ["skill-mutation-testing-validating-your-test-suite-93dbce25ed"]
---

## Property-Based Testing with Hypothesis

### When to Use Property-Based Testing
Property-based testing (Hypothesis) finds edge cases that example-based tests miss. Use it for:

| Good fit | Poor fit |
|---|---|
| Pure functions (no side effects) | UI flows |
| Data transformations | Performance testing |
| Serialization / deserialization | Complex setup/teardown scenarios |
| Parsers and validators | Anything requiring real external services |
| Mathematical operations | |
| State machines | |
| Round-trip properties (encode → decode = original) | |

### How Hypothesis Works
1. Generates inputs based on your strategy specifications
2. Runs your test with hundreds/thousands of generated inputs
3. When it finds a failure, **shrinks** the input to the minimal failing case
4. Reports the minimal reproduction

Shrinking is what makes property-based testing practical: the actual failing input might be 10,000 characters, but Hypothesis shrinks it to `""` or `"a"` — the root cause.

### Common Properties to Test

```python
# Round-trip: encode then decode returns original
@given(st.text())
def test_json_round_trip(s):
    assert json.loads(json.dumps({"value": s}))["value"] == s

# Invariant: sorted list is always ordered
@given(st.lists(st.integers()))
def test_sort_preserves_all_elements(lst):
    sorted_lst = sorted(lst)
    assert len(sorted_lst) == len(lst)
    assert sorted(sorted_lst) == sorted_lst

# Commutativity: order doesn't matter
@given(st.integers(), st.integers())
def test_addition_is_commutative(a, b):
    assert a + b == b + a

# No crash guarantee: valid inputs should never raise unexpected exceptions
@given(st.text(min_size=1, max_size=255))
def test_username_validation_never_crashes(username):
    try:
        result = validate_username(username)
        assert isinstance(result, bool)  # always returns a bool
    except ValueError:
        pass  # ValueError is acceptable for invalid inputs
    # Any other exception is a bug
```

---
