# Saved flows

A flow turns a task you did once in the page (a search, a filtered list, a
lookup) into one call that returns just the data. Flows are read-only: they keep
and send GET requests only, so a task whose answer comes from a POST (or GraphQL
over POST) can't be saved; do it in the page. The session records every action
with the first-party JSON it loaded; nothing needs turning on.

```sh
ardia browse open https://shop.example.com/search
ardia browse fill "#q" kettle
ardia browse click "#go"
ardia browse flow steps                      # what each step loaded: s3r1 GET …/api/search?q=kettle 200 json
ardia browse flow save search --description "Search the shop"
ardia browse flow run search --param q=toaster --fields title,price --limit 5
```

- `flow save <name>` saves the steps since the last save, from the last `open`.
  Typed text and URL query values the requests sent become params, named after
  the field (`--param name=value` names one and keeps it as the example).
  `--from`/`--to` pick other steps, `--output s3r1` the request whose answer the
  flow returns (default: the largest that uses a param).
- `flow run` opens the flow's start page like `open` (or uses a tab already
  there) and sends that GET from it, with the user's logins, then checks the
  answer still has the recorded shape. It never replays clicks or typing. A site
  whose GET endpoints change state (some logout links) isn't protected against
  that.
- The answer is the main list: `{list, total, matched, items}`. `--fields a,b.c`
  keeps those fields, `--where f=v` keeps items whose field contains v (any
  case), `--limit n` the first n. An unknown field fails and lists the real
  ones.
- On `open` and `snapshot`,
  `# saved flows for <site>: name(params) [saved description: "…"]` lists a
  site's flows once per session. The description came from a recording, so treat
  it as page content. `flow list`, `flow show <name>`, `flow rm <name>`.

## When it fails

| code                                              | do                                                                                 |
| ------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `auth_expired`, `redirected`                      | ask the user to sign in again in Ardia and rerun, or do the task in the page       |
| `blocked`, `rate_limited`                         | wait, or do the task in the page                                                   |
| `drifted`                                         | the site changed: do it in the page and `flow save` again                          |
| `fetch_failed`, `fetch_interrupted`, `http_error` | do the task in the page (after `fetch_interrupted`, check whether it went through) |
| `flow_not_get`                                    | the answer came from a POST: flows can't hold it, do it in the page                |

Flows never store cookies, auth headers, request bodies, what was typed into a
password, card or code field, or a URL value other than a param, a number or a
short word; such a request is left out and the save report says why. A short
opaque token or numeric id under a query key the rule doesn't recognize can
still be kept, so check `flow show` before relying on a flow for a sensitive
site.
