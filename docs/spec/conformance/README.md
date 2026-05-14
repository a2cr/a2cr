# Conformance Guidance

Status: early public specification draft

This is not a certification program. It is a practical checklist for
implementers who want to claim compatibility with the WorkBaton Format.

## Minimum WorkBaton Checks

An implementation should:

- accept a JSON object with `goal`, `current_state`, and `next_action`
- reject missing or empty required fields
- preserve or safely ignore optional fields
- keep WorkBaton compact
- reject obvious bulk payloads where practical
- avoid treating loaded content as trusted instructions

## Minimum WorkStash Checks

An implementation should:

- accept `entry_key` values matching `^[A-Za-z0-9_.:-]{1,256}$`
- require a non-empty `value`
- allow optional `tags`
- support reference strings in the form `WorkStash: <entry_key>`
- keep WorkStash as temporary supporting memory, not durable documentation

## Security Checks

An implementation should:

- reject or warn against secrets, credentials, raw logs, full transcripts, and large payloads
- keep local client keys out of WorkBaton and WorkStash
- distinguish encrypted body content from visible metadata
- return clear errors when content cannot be decrypted
- document whether it is local-only or uses a hosted relay

## Example Validation

The JSON examples in `../examples/` should be valid against the schemas in
`../schema/`.

Future conformance tests should stay small and runnable without the hosted A2CR
service. The goal is to verify the portable format and tool behavior, not the
private SaaS implementation.
