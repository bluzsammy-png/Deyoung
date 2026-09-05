# ARTIFACT_SPEC.md

Artifacts are the durable outputs of PATI: files produced by workers
(videos, images, audio, reports, manifests) or registered references to
bytes that live on the owner's disk.

## Fields (schemas/artifact.schema.json)

artifact_id, task_id, stage_id, worker_id, name, type, mime_type, location,
storage (control_plane | local_reference), size, checksum (sha256),
retention, visibility, provenance, metadata, created_at.

## Storage modes

- **control_plane**: bytes in the content-addressed store
  (`<data>/artifacts/<aa>/<sha256>`); dedup by checksum; atomic writes via
  temp-file rename; served by `GET /artifacts/{id}/content`.
- **local_reference**: bytes stay on the Local Agent's disk (authorized
  folder); PATI records path + checksum + size. Content endpoint returns
  409 LOCAL_REFERENCE with the location. A later `artifact.save` stage can
  copy it locally or a remote worker can re-upload it.

## Provenance

`provenance` records: producing worker (id/type), job, model/tool version
when applicable, prompt/config pointers, and the uploading token. The
metadata block carries stage-specific details (e.g., project name, file
counts for manifests).

## Rules

- Every artifact is checksummed at creation; sizes are enforced against
  MAX_UPLOAD_MB and the per-tenant storage quota.
- Artifacts are tenant-scoped; reads re-check ownership.
- Deletion is an admin operation and is audited.
- Nothing is ever fabricated: a worker that produced nothing returns no
  artifact; failed stages have no artifacts.
