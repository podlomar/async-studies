# Coding Guide

Rules below are **not** enforced by the linter or compiler and must be followed manually.

## Comments

Default to no comments. Only add one when the **why** is non-obvious — a hidden constraint, a workaround for a specific bug, or behaviour that would surprise a reader. Well-named identifiers make the what self-evident; comments explain what they cannot.

```ts
// ✅
// must run before the router mounts or redirects fire before auth is ready
await authStore.init();

// ❌ — restates what the code already says
// initialize the auth store
await authStore.init();
```

## Naming

Use descriptive names that make intent clear. Avoid abbreviations and single-letter variables except in short lambdas or conventional loop counters.

```ts
// ✅
const invoiceTotal = calculateTotal(lineItems);
const users = await fetchActiveUsers();
lineItems.filter(item => item.quantity > 0);

// ❌
const t = calc(li);
const u = await fetch2();
li.filter(i => i.q > 0);
```

Functions should start with a verb that describes what they do. Use common prefixes consistently: `get`/`fetch` for retrieval, `create`/`build` for construction, `update`/`set` for mutation, `delete`/`remove` for deletion, `handle` for event handlers, `validate`/`check` for assertions, `is`/`has`/`can` for booleans.

```ts
// ✅
const fetchUserById = (id: number): Promise<User> => { ... }
const isEmailValid = (email: string): boolean => { ... }
const handleSubmit = (event: SubmitEvent): void => { ... }

// ❌
const userData = (id: number): Promise<User> => { ... }
const emailValid = (email: string): boolean => { ... }
const submitAction = (event: SubmitEvent): void => { ... }
```

## Function size

A function should do one thing. If the body needs comments to explain its sections, split it into smaller functions.

```ts
// ✅
const validateForm = (form: Form): ValidationResult => { ... }
const submitForm = async (form: Form): Promise<void> => {
  const result = validateForm(form);
  if (result.valid !== true) {
    return;
  }
  await api.submit(form);
}

// ❌
const handleForm = async (form: Form): Promise<void> => {
  // validate
  if (!form.email) { ... }
  // submit
  await api.submit(form);
}
```

## Magic numbers and strings

Extract unexplained literals into named constants.

```ts
// ✅
const MAX_RETRY_ATTEMPTS = 3;
const DEFAULT_TIMEOUT_MS = 5000;
if (attempts > MAX_RETRY_ATTEMPTS) { ... }

// ❌
if (attempts > 3) { ... }
setTimeout(callback, 5000);
```

## Early returns

Return early on invalid or edge-case conditions at the top of a function rather than wrapping the main logic in nested branches.

```ts
// ✅
const processOrder = (order: Order): void => {
  if (order.items.length === 0) {
    return;
  }

  if (order.status !== "pending") {
    return;
  }

  // main logic
}

// ❌
const processOrder = (order: Order): void => {
  if (order.items.length > 0) {
    if (order.status === "pending") {
      // main logic
    }
  }
}
```

## Error handling

Only validate and handle errors at system boundaries — user input and external APIs. Trust internal code and framework guarantees; don't add defensive checks for states that cannot occur.

```ts
// ✅ — validate at the API boundary
const handler = (req: Request): Response => {
  if (req.body.email === undefined) return badRequest("email required");
  return processEmail(req.body.email);
}

// ❌ — redundant guard inside trusted internal code
const processEmail = (email: string): void => {
  if (email === undefined) {
    throw new Error("email required");
  }
  ...
}
```
