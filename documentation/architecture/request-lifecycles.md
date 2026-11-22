# Request and response lifecycles

**Status: Current conceptual workflow. Exact endpoints and asynchronous behaviour require code verification.**

## Studio operation

A Studio client authenticates, calls the API, is authorized against its project or survey context, and receives a result from a feature operation. Persistence is mediated by repositories.

## Participant admission

A participant link resolves to a permitted survey or assigned participant context. The application loads the relevant published survey version and establishes the participant workflow.

## Response submission

Answers are validated against the published survey contract and written through the response persistence boundary. Identifying context and answer storage remain separately scoped.

Optimization proposals involving short-lived scoped tokens, CDN bootstrap and speculative authorization must not be treated as deployed behaviour until implemented and verified.
