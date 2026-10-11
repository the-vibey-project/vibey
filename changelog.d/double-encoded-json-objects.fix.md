* **A model's JSON object written as a string is read as the object, not re-asked:** gpt-oss in JSON
  mode wrote the second item of a two-item work plan as a string holding the whole item, encoded a
  second time with every quote escaped. The plan was otherwise sound, but the schema check named
  `$.items[1] must be of JSON type object, got string` and the whole plan was regenerated, a second
  model call and minutes on a local model. Parsing that string gives exactly the object that was
  meant, so every sovereign producer (the interview questions, the spec, the research summary and
  the work plan) now reads a string as an object where the schema says `object` and the string's
  whole text is a JSON object. Any other string stays, and the check names it as before.
