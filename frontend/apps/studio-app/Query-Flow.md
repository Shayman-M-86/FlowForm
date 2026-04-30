Here’s a cleaner formatted version:




# FlowForm Studio App Flow

This explains the full flow from the browser to the backend, file by file.

---

## 1. App Boot

**File:** `frontend/apps/studio-app/src/main.tsx`

Everything starts here.

The app is wrapped with three providers:

- `Auth0Provider` — gives every component access to Auth0 state and methods.
- `QueryClientProvider` — gives every component access to React Query's cache.
- `ThemeProvider` — handles dark/light mode.

The router renders inside all of these providers, so every route has access to authentication, query state, and theme state.

---

## 2. Route Rendering

**File:** `frontend/apps/studio-app/src/routes/__root.tsx`

This is the TanStack Router root route.

Every page renders through this file.

`ProtectedApp` wraps `<Outlet />`, which means no route renders until authentication has been resolved.

---

## 3. Auth Gate

**File:** `frontend/apps/studio-app/src/components/auth/ProtectedApp.tsx`

This component controls whether the app should render, show the sign-in screen, or bootstrap the user.

### Flow

```txt
Page loads
  ↓
Check sessionStorage for "flowform.bootstrapped"
  ↓
Already bootstrapped?
  ├─ Yes → render children immediately
  └─ No  → wait for Auth0 silent check
              ↓
          Auth0 resolves
              ↓
          Authenticated?
            ├─ No → show sign-in screen
            └─ Yes
                 ↓
              Same user?
                ├─ Yes → setBootstrapReady(true), render children
                └─ No  → run bootstrap
                            ↓
                         POST /api/v1/auth/bootstrap-user
                         with ID token
                            ↓
                         Save result to sessionStorage:
                         - flowform.user
                         - flowform.avatar
                            ↓
                         Render children
```

When `ProtectedApp` renders its children, it wraps them in `UserProvider`.

---

## 4. User Context

**File:** `frontend/apps/studio-app/src/auth/UserContext.tsx`

This holds the current user profile in React context.

Any component can call:

```ts
useCurrentUser()
```

It returns:

```ts
{
  user: CurrentUserOut;
  displayName: string;
  avatarUrl: string | null;
}
```

### Data sources

* `user` comes from the backend bootstrap response.
* On refresh, `user` can be restored from `sessionStorage`.
* `avatarUrl` comes from the Auth0 profile picture claim.
* The avatar is also persisted to `sessionStorage`.

---

## 5. Making API Calls

**File:** `frontend/apps/studio-app/src/api/useApi.ts`

This file returns an `executor`.

The executor exposes:

```ts
get()
post()
patch()
del()
getWithQuery()
```

Every method automatically:

1. Calls `getAccessTokenSilently()` to get a fresh Auth0 access token.
2. Adds the token to the request as an `Authorization` header.
3. Calls the raw fetch function.

The token used here is an **access token**, not the ID token.

It is scoped to:

```txt
VITE_AUTH0_AUDIENCE
```

Auth0 handles refreshing the token silently.

---

## 6. Raw HTTP Client

**File:** `frontend/apps/studio-app/src/api/client.ts`

This file contains plain `fetch` wrappers.

It does not handle authentication.

Its responsibilities are:

* Build the request.
* Send it to `VITE_API_BASE_URL`.
* Parse the JSON response.
* Throw `ApiRequestError` when the request fails.
* Return `undefined` for `204 No Content` responses.

---

## 7. Query Hooks

**File:** `frontend/apps/studio-app/src/api/projects.ts`

This is where React Query logic lives.

Each hook follows this pattern:

1. Call `useApi()` to get the executor.
2. Pass the executor to a plain fetcher function.
3. Wrap the fetcher in `useQuery` or `useMutation`.

React Query owns the cache.

For example:

```ts
projectKeys.list()
```

Produces the query key:

```ts
['projects', 'list']
```

That query key is the cache address.

If two components call `useProjects()`, they share the same cached request.

---

## 8. Types

**File:** `frontend/apps/studio-app/src/api/types.ts`

This file contains shared request and response types.

Examples:

```ts
ProjectOut
SurveyOut
CurrentUserOut
ApiExecutor
ApiError
```

This file should stay as a base layer.

It should not import from the rest of the app.

---

# Full Call Chain: Loading Projects

```txt
ProjectsPage calls useProjects()
  ↓
api/projects.ts
  ↓
useApi()
  ↓
Gets executor
  ↓
useQuery({
  queryKey: ['projects', 'list'],
  queryFn: () => fetchProjects(executor)
})
  ↓
React Query checks cache
  ↓
Cache hit and fresh?
  ├─ Yes → return cached data, no network request
  └─ No  → call fetchProjects(executor)
              ↓
          api/projects.ts
              ↓
          executor.get('/api/v1/projects')
              ↓
          api/useApi.ts
              ↓
          getAccessTokenSilently()
              ↓
          Auth0 returns Bearer token
              ↓
          client.get('/api/v1/projects', {
            Authorization: 'Bearer ...'
          })
              ↓
          api/client.ts
              ↓
          fetch('http://localhost:5000/api/v1/projects', ...)
              ↓
          Parse JSON
              ↓
          Return ProjectOut[]
              ↓
          Component receives:
          - data
          - isPending
          - isError
              ↓
          Render project list
```

---

# Full Call Chain: Creating a Project

```txt
CreateProjectForm calls useCreateProject()
  ↓
api/projects.ts
  ↓
Returns { mutate, isPending }
  ↓
User submits form
  ↓
mutate({
  name: 'My Project',
  slug: 'my-project'
})
  ↓
executor.post('/api/v1/projects', body)
  ↓
getAccessTokenSilently()
  ↓
Auth0 returns Bearer token
  ↓
client.post('/api/v1/projects', body, headers)
  ↓
fetch POST request
  ↓
Backend returns new ProjectOut
  ↓
onSuccess fires
  ↓
queryClient.invalidateQueries(['projects', 'list'])
  ↓
React Query marks the project list as stale
  ↓
React Query refetches in the background
  ↓
ProjectsPage re-renders with the new data
```

---

# Where to Add Things

| Task                                           | Location                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------- |
| Add a new API response type                    | `api/types.ts`                                                                  |
| Add a new resource like surveys or submissions | Create a new file like `api/surveys.ts` following the `api/projects.ts` pattern |
| Add a new page                                 | Add it to `pages/` and register it in `routes/`                                 |
| Access the current user                        | Use `useCurrentUser()` from `auth/UserContext.tsx`                              |
| Access raw Auth0 state                         | Use `useAuth0()` from `@auth0/auth0-react`                                      |
