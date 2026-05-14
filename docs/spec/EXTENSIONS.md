# Extension Guidance

Status: early public specification draft

The WorkBaton Format should stay small. Extensions are allowed, but they should
not make basic handoff depend on private fields.

## Preferred Extension Shape

Use the `extensions` object with namespaced keys:

```json
{
  "extensions": {
    "example.com/review_status": "needs-human-review"
  }
}
```

Namespacing helps avoid collisions between tools.

## Experimental Top-Level Fields

Experimental top-level fields may use `x_` or `x-` prefixes:

```json
{
  "x_client_hint": "keep-local"
}
```

Do not require another implementation to understand experimental fields in
order to use the core baton.

## When To Propose A Core Field

Consider proposing a field for the core specification when:

- multiple independent implementations need it
- the meaning is clear without product-specific context
- it can be documented without exposing private service details
- it does not encourage storing secrets or bulk data
