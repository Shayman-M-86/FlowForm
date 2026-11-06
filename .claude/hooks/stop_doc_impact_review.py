"""Compatibility entry point for chats caching the retired Stop hook.

The current .codex/hooks.json intentionally omits automatic documentation
review. Older chats may retain this command after switching branches, so keep
the former path callable without restoring the retired hook's behavior.
"""

if __name__ == "__main__":
    raise SystemExit(0)
