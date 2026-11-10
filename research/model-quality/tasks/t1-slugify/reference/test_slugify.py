from slugify import slugify

assert slugify("Hello,  World!") == "hello-world"
assert slugify("  x  ") == "x"
assert slugify("A_B") == "a-b"
assert slugify("") == ""
