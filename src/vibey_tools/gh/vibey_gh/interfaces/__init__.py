# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey-gh's seams -- declared here, implemented beside the module that needs them.

One module per collaborator, named after it with an `_interface` suffix, mirroring the
package it describes: `vibey_gh/review_contract.py` is declared by
`vibey_gh/interfaces/review_contract_interface.py`. Interfaces DECLARE; they never
consume -- nothing in here imports an implementation, so a caller can type against a seam
without dragging the implementation in behind it.
"""

from __future__ import annotations

from vibey_gh.interfaces.review_contract_interface import ReviewContractPort

__all__ = ["ReviewContractPort"]
