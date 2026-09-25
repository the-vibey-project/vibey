{{- define "vibey.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vibey.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "vibey.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vibey.labels" -}}
app.kubernetes.io/name: {{ include "vibey.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "vibey.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "vibey.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
The DSN is the one piece of config that must never be assembled in two
places: an existing Secret wins outright, otherwise the built-in postgres
Service is addressed by its in-cluster DNS name.
*/}}
{{- define "vibey.dsnSecretName" -}}
{{- if .Values.dsn.existingSecret -}}
{{- .Values.dsn.existingSecret -}}
{{- else -}}
{{- printf "%s-dsn" (include "vibey.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "vibey.dsnSecretKey" -}}
{{- if .Values.dsn.existingSecret -}}
{{- .Values.dsn.existingSecretKey -}}
{{- else -}}
dsn
{{- end -}}
{{- end -}}

{{/*
The owner's DSN (ADR-0055): the role that runs migrations and owns the tables.
Empty means a single-DSN install -- an existing Secret whose owner key is not
named (`dsn.existingSecretMigrateKey`, empty by default) -- where the worker
migrates as the one role and `vibey doctor` reports the ledger guard as not in
force.
*/}}
{{- define "vibey.migrateSecretKey" -}}
{{- if .Values.dsn.existingSecret -}}
{{- .Values.dsn.existingSecretMigrateKey -}}
{{- else -}}
migrate-dsn
{{- end -}}
{{- end -}}

{{/*
`vibey migrate`, as an init container: the only place the owner's DSN is mounted.
It applies migrations, creates the application role if it is missing, and grants it
exactly the declared privileges, then fails the pod if the application's DSN could
still rewrite the ledger. The workload that follows gets the application's DSN only.
*/}}
{{- define "vibey.migrateInitContainer" -}}
{{- if include "vibey.migrateSecretKey" . }}
- name: migrate
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  args: ["migrate"]
  env:
    - name: VIBEY_PG_MIGRATE_URL
      valueFrom:
        secretKeyRef:
          name: {{ include "vibey.dsnSecretName" . }}
          key: {{ include "vibey.migrateSecretKey" . }}
    - name: VIBEY_PG_URL
      valueFrom:
        secretKeyRef:
          name: {{ include "vibey.dsnSecretName" . }}
          key: {{ include "vibey.dsnSecretKey" . }}
  securityContext: {{- toYaml .Values.securityContext | nindent 4 }}
{{- end }}
{{- end -}}

{{/*
worker.project is a UUID, and two readers need it: the worker's --project
argument and the KEDA scaler's SQL. The SQL is why it is checked here --
a value interpolated into a query has to be proven to be the shape it
claims before it gets there. Every spelling Python's uuid.UUID accepts
(braces, a urn:uuid: prefix, hyphens or none) is accepted; what reaches
SQL is the bare 32 hex digits, which PostgreSQL's uuid input reads as-is.
*/}}
{{- define "vibey.workerProjectHex" -}}
{{- $raw := .Values.worker.project | toString | lower -}}
{{- $hex := $raw | replace "urn:" "" | replace "uuid:" "" | replace "{" "" | replace "}" "" | replace "-" "" -}}
{{- if not (regexMatch "^[0-9a-f]{32}$" $hex) -}}
{{- fail (printf "worker.project must be a project UUID (the id `vibey new` prints), got %q" (toString .Values.worker.project)) -}}
{{- end -}}
{{- $hex -}}
{{- end -}}

{{/*
The in-cluster Ollama endpoint, fully qualified for the same reason the DSN
is: a bare Service name resolves only inside this namespace, and nothing
guarantees every reader lives here. Root form, no path -- vibey's own
client wants the server root; the local runner's OpenAI-compatible backend
(gptossloop, and qwenloop when on) appends /v1 where it is wired, in
worker.yaml.
*/}}
{{- define "vibey.ollamaURL" -}}
{{- printf "http://%s-ollama.%s.svc.%s:%v" (include "vibey.fullname" .) .Release.Namespace .Values.clusterDomain .Values.ollama.service.port -}}
{{- end -}}

{{- define "vibey.ollamaImage" -}}
{{- $image := .Values.ollama.image -}}
{{- if $image.digest -}}
{{- printf "%s:%s@%s" $image.repository (toString $image.tag) $image.digest -}}
{{- else -}}
{{- printf "%s:%s" $image.repository (toString $image.tag) -}}
{{- end -}}
{{- end -}}

{{/*
The pull Job's pod template, kept in one place so its hash can name the Job.
A Job's pod template is immutable: an upgrade that changed any of it under
the same name would fail outright. Naming the Job after the template means
a changed model, image or endpoint is a NEW Job (and the old one is pruned
with the release), while an upgrade that changes none of it re-applies the
same object and pulls nothing. The labels here are deliberately the stable
selector set, not vibey.labels: those carry the chart version, which would
make every chart bump a re-pull for no reason.
*/}}
{{- define "vibey.ollamaPullTemplate" -}}
metadata:
  labels:
    app.kubernetes.io/name: {{ include "vibey.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/component: ollama-pull
spec:
  restartPolicy: Never
  securityContext: {{- toYaml .Values.ollama.podSecurityContext | nindent 4 }}
  containers:
    - name: pull
      image: {{ include "vibey.ollamaImage" . | quote }}
      imagePullPolicy: {{ .Values.ollama.image.pullPolicy }}
      # The ollama image has no curl. Its own CLI is the client instead:
      # `ollama pull` POSTs /api/pull to the server named by OLLAMA_HOST and
      # streams progress, and the weights land on the server's volume, not
      # here. The model reaches the shell as an environment variable, never
      # spliced into the script, so a value cannot become a command.
      command: ["sh", "-c"]
      args:
        - |
          set -eu
          # The Job and the server start together. A pull against a server
          # that is not listening yet is an attempt burned for nothing.
          until ollama list >/dev/null 2>&1; do
            echo "waiting for ollama at $OLLAMA_HOST"
            sleep 5
          done
          {{- if .Values.ollama.qwenloopFeature }}
          ollama pull "$OLLAMA_PULL_MODEL"
          # qwenloop's Qwen model, beside the default (ADR-0064).
          exec ollama pull "$OLLAMA_PULL_QWEN_MODEL"
          {{- else }}
          exec ollama pull "$OLLAMA_PULL_MODEL"
          {{- end }}
      env:
        - name: OLLAMA_HOST
          value: {{ include "vibey.ollamaURL" . | quote }}
        - name: OLLAMA_PULL_MODEL
          value: {{ required "ollama.model is required when ollama.pull.enabled" .Values.ollama.model | quote }}
        {{- if .Values.ollama.qwenloopFeature }}
        - name: OLLAMA_PULL_QWEN_MODEL
          value: {{ required "ollama.qwenModel is required when ollama.qwenloopFeature" .Values.ollama.qwenModel | quote }}
        {{- end }}
        # The client never needs a home of its own; point it somewhere a
        # non-root uid can write rather than at an unwritable "/".
        - name: HOME
          value: /tmp
      securityContext: {{- toYaml .Values.ollama.securityContext | nindent 8 }}
      resources: {{- toYaml .Values.ollama.pull.resources | nindent 8 }}
{{- end -}}

{{/*
Format a container image from a dictionary with repository, tag, and optional digest.
*/}}
{{- define "vibey.image" -}}
{{- $img := . -}}
{{- if $img.digest -}}
{{- printf "%s:%s@%s" $img.repository (toString $img.tag) $img.digest -}}
{{- else -}}
{{- printf "%s:%s" $img.repository (toString $img.tag) -}}
{{- end -}}
{{- end -}}

{{/*
Format a fully qualified in-cluster Service URL for an operational surface component.
Usage: include "vibey.surfaceURL" (dict "root" $ "name" "component-name" "port" 1234 "scheme" "http")
*/}}
{{- define "vibey.surfaceURL" -}}
{{- $scheme := default "http" .scheme -}}
{{- printf "%s://%s-%s.%s.svc.%s:%v" $scheme (include "vibey.fullname" .root) .name .root.Release.Namespace .root.Values.clusterDomain .port -}}
{{- end -}}


{{/*
The environment variable a surface database's password reaches the postgres
container under: VIBEY_DB_PASSWORD_<NAME>, upper-cased, non-alphanumerics as _.
*/}}
{{- define "vibey.surfaceDbPasswordEnv" -}}
{{- printf "VIBEY_DB_PASSWORD_%s" (regexReplaceAll "[^A-Z0-9]" (upper .) "_") -}}
{{- end -}}

{{/*
A surface database's own password (postgres.additionalDatabasePasswords), which
must be set: a surface without one would have no role but the owner to use.
*/}}
{{- define "vibey.surfaceDbPassword" -}}
{{- $password := index .root.Values.postgres.additionalDatabasePasswords .name -}}
{{- if not $password -}}
{{- fail (printf "postgres.additionalDatabasePasswords.%s must be set: each surface database has a role of its own (ADR-0055)" .name) -}}
{{- end -}}
{{- $password -}}
{{- end -}}
