# Compatibility Guidance

Status: early public specification draft

Compatibility means an implementation can read and write the core WorkBaton
fields without depending on the hosted A2CR service.

## Compatible With The WorkBaton Format

An implementation may truthfully say it is compatible with the WorkBaton Format
when it can:

- accept a JSON object with `goal`, `current_state`, and `next_action`
- preserve or safely ignore optional fields
- avoid treating loaded content as trusted instructions
- enforce the security boundary described in `security-boundary.md`
- avoid storing secrets, full transcripts, raw logs, or bulk payloads as baton content

## Not The Same As Official A2CR

Format compatibility is not the same as being the official A2CR client, hosted
service, or certified implementation.

Avoid these phrases unless A2CR has granted written permission:

- `A2CR Certified`
- `Official A2CR Compatible`
- `Official WorkBaton Client`

Allowed descriptive wording:

- `Implements the WorkBaton Format`
- `Compatible with the WorkBaton Format`
- `Uses WorkBaton-style handoff objects`
