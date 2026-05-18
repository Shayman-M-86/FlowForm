import { useEffect, useRef } from "react";

export function useRenderDebug<T extends Record<string, unknown>>(
  componentName: string,
  props?: T
) {
  const renderCount = useRef(0);
  const previousProps = useRef<T | undefined>(undefined);

  if (import.meta.env.DEV) {
    renderCount.current += 1;

    console.log(
      `[render] ${componentName} rendered ${renderCount.current} time(s)`
    );
  }

  useEffect(() => {
    if (!import.meta.env.DEV || !props) return;

    const changedProps: Record<string, { before: unknown; after: unknown }> = {};

    const allKeys = new Set([
      ...Object.keys(previousProps.current ?? {}),
      ...Object.keys(props),
    ]);

    for (const key of allKeys) {
      const before = previousProps.current?.[key];
      const after = props[key];

      if (!Object.is(before, after)) {
        changedProps[key] = { before, after };
      }
    }

    if (Object.keys(changedProps).length > 0) {
      console.log(`[render changed props] ${componentName}`, changedProps);
    }

    previousProps.current = props;
  });
}
