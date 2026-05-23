# JavaScript Style Guide

Tooling configs: [biome.json](../../templates/biome.json) · [tsconfig.json](../../templates/tsconfig.json)

Rules below are **not** enforced by the linter or compiler and must be followed manually.

## Functions

Always use arrow functions instead of function declarations or expressions.

```ts
// ✅
const getUser = (id: number): User => { ... }

// ❌
function getUser(id: number): User { ... }
const getUser = function(id: number): User { ... }
```

All functions must have an explicit return type annotation. Biome's `useExplicitType` rule covers this but is currently in nursery — add it to `biome.json` once it stabilizes.

```ts
// ✅
const getUser = (id: number): User => { ... }

// ❌
const getUser = (id: number) => { ... }
```

No explicit `return undefined` — use a bare `return` or omit it entirely. Enforced by Biome's `noUselessUndefined`.

```ts
// ✅
const validate = (x: string): void => { if (!x) return; }

// ❌
const validate = (x: string): void => { if (!x) return undefined; }
```

## Async

When calling a function that returns a promise without awaiting it, use `void` to make the intent explicit. Biome's `noFloatingPromises` rule covers this but is currently in nursery — add it to `biome.json` once it stabilizes.

```ts
// ✅
void analytics.track("page_view");

// ❌
analytics.track("page_view");
```

## Boolean expressions

No implicit boolean coercion. Always use explicit comparisons.

```ts
// ✅
if (value !== null && value !== undefined) { ... }
if (list.length > 0) { ... }
if (isActive === true) { ... }

// ❌
if (value) { ... }
if (list.length) { ... }
if (isActive) { ... }
```

## Nullish coalescing

Use `??` instead of `||` for default values. `||` triggers on any falsy value (`0`, `""`, `false`), which is rarely the intent. Biome's `useNullishCoalescing` rule covers this but is currently in nursery — add it to `biome.json` once it stabilizes.

```ts
// ✅
const port = config.port ?? 3000;
const label = user.name ?? "Anonymous";

// ❌
const port = config.port || 3000;
const label = user.name || "Anonymous";
```

## Unknown over any

Use `unknown` instead of `any` when the type is genuinely not known. `any` silences the type checker entirely; `unknown` forces you to narrow the type before use.

```ts
// ✅
const parse = (input: unknown): User => {
  if (!isUser(input)) throw new Error("invalid input");
  return input;
}

// ❌
const parse = (input: any): User => {
  return input;
}
```

## Nested ternaries

Do not nest ternaries. Use `if/else` or extract the logic into a named variable or function.

```ts
// ✅
const getLabel = (status: Status): string => {
  if (status === "active") {
    return "Active";
  }
  
  if (status === "pending") {
    return "Pending";
  }
  
  return "Inactive";
}

// ❌
const label = status === "active" ? "Active" : status === "pending" ? "Pending" : "Inactive";
```

## Exports

Use named exports only. Default exports make refactoring and IDE rename support harder.

```ts
// ✅
export const UserCard = () => { ... }
export const formatDate = (date: Date): string => { ... }

// ❌
export default function UserCard() { ... }
```

## Linting suppressions

Do not disable linting rules without an explanation comment.

```ts
// ✅
// biome-ignore lint/suspicious/noExplicitAny: third-party callback has no type definition
const handler = (data: any) => { ... }

// ❌
// biome-ignore lint/suspicious/noExplicitAny
const handler = (data: any) => { ... }
```

Use `@ts-expect-error` instead of `@ts-ignore`, always with an explanation.

```ts
// ✅
// @ts-expect-error: missing type in outdated library definition
foo.bar();

// ❌
// @ts-ignore
foo.bar();
```
