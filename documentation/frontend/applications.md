# Frontend applications

**Status: Current product surfaces; implementation specifics remain repository-owned.**

The public website introduces FlowForm and offers a browser-only builder demonstration. Studio is the authenticated management interface. The participant experience is the survey-taking interface.

Each application owns its navigation, presentation state and interaction behaviour. API-backed capabilities must honor the backend's resource contracts and permission decisions. Shared interface elements and survey rendering utilities belong in a reusable frontend package only when they serve more than one application.

Source: [FlowForm frontend](https://github.com/Shayman-M-86/FlowForm/tree/main/frontend).
