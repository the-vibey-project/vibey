* **sovereign runner:** the job container now sits on a Docker network with no route out, and
  its only way out is an egress gate (`[runners] egress_gate`, on by default). The gate
  forwards four model-server requests (version, tags, models, chat completions) and tunnels
  HTTPS to a short list of hosts (`egress_allow`: GitHub and its artifact stores, PyPI), to
  globally routable addresses only. Before, `--add-host host-gateway` exposed every port on
  the host to a job's shell, and the host's Postgres and RabbitMQ accepted connections from
  inside the container. `vibey-gh runner install` renders the gate (`egress/`), the network and
  the proxy settings; `runner check` reports drift in them. Turning the gate off is a declared,
  documented choice, and the backlog prompt that runs on the host refuses to run without it.
