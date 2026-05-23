# React Style Guide

Rules below are **not** enforced by the linter or compiler and must be followed manually.

## State

Combine related state into a single `useState` call instead of splitting values that change together. This especially applies to async loading state — `data`, `error`, and `isLoading` always transition together and must be modelled as one state object.

```ts
// ✅
const [form, setForm] = useState({ name: "", email: "" });

const [request, setRequest] = useState<
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: User }
  | { status: "error"; error: string }
>({ status: "idle" });

// ❌
const [name, setName] = useState("");
const [email, setEmail] = useState("");

const [isLoading, setIsLoading] = useState(false);
const [data, setData] = useState<User | null>(null);
const [error, setError] = useState<string | null>(null);
```
