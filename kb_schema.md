# Knowledge-Base Schema

The canonical interchange format is a JSON object with two top-level keys.

## Top level

```json
{ "courses": { ... }, "students": { ... } }
```

- `courses`: object mapping course id (string) → course object.
- `students`: object mapping student id (string) → student object.

## Course object

```json
{ "prerequisite": <expr>, "corequisites": ["CS201"] }
```

- `prerequisite`: `null`, a course id string, or a nested expression
  `{"and": [<expr>, ...]}` / `{"or": [<expr>, ...]}`. `and`/`or` arrays are
  non-empty and may nest arbitrarily.
- `corequisites`: list of course ids the student must be concurrently `taking`.

## Student object

```json
{ "completed": ["CS101"], "taking": ["CS201"], "waivers": [{"course": "CS202", "prerequisite": "MATH101"}] }
```

- `completed`: course ids the student has finished.
- `taking`: course ids the student is currently enrolled in.
- `waivers`: list of `{course, prerequisite}` — a waiver scoped to
  `(student, target course, prerequisite)`.

## Validity rules

Every course id referenced anywhere (prerequisite expressions, corequisites,
`completed`, `taking`, waivers) must exist in `courses`.

## Reasoning semantics

- A prerequisite `P` of course `C` is satisfied by `completed(S,P)` **or**
  `waiver(S,C,P)`. Being *eligible* for `P` does **not** satisfy `C`'s
  prerequisite (`eligibility != completion`).
- `AND` requires every child; `OR` requires at least one.
- A corequisite `Q` is satisfied by `taking(S,Q)` only.
