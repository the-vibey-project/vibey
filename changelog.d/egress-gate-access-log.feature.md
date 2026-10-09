* **sovereign runner:** the egress gate now logs every decision on its standard output
  (`docker logs vibey-egress`): `egress ALLOW github.com:443`, or `egress DENY example.com:443
  -- not on the allowlist (add the host to [runners] egress_allow)`, with a reason for each of
  its refusals (not listed, not a host:port, does not resolve, resolves to a non-public
  address, upstream down, a model request that is not one of the four allowed). Before, a job
  step that failed on an unlisted host got a bare 403 and the gate said nothing. Only the
  destination and the reason are written, never a header, a body or a credential, and
  client-supplied text is cleaned and cut so it cannot forge a line.
