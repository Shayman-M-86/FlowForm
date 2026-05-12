import { useEffect, useRef } from "react";

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

const GRID_GAP = 35;

function getCanvasColor(): string {
  const token = getComputedStyle(document.documentElement)
    .getPropertyValue("--muted-foreground")
    .trim();

  if (!token) return "rgb(120 120 128)";
  if (/^-?\d/.test(token)) return `hsl(${token})`;
  return token;
}

export function PlusGridAnimation() {
  const layerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    const state = {
      color: getCanvasColor(),
      frameId: 0,
      height: 0,
      layerTop: 0,
      viewportHeight: window.innerHeight,
      viewportOffsetTop: 0,
      width: 0,
    };

    const resizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const layer = layerRef.current;
      const host = layer?.parentElement;
      const layerRect = layer?.getBoundingClientRect();
      const hostRect = host?.getBoundingClientRect();
      const viewport = window.visualViewport;

      state.width = hostRect?.width || layerRect?.width || window.innerWidth;
      state.height = Math.max(
        host?.scrollHeight || 0,
        hostRect?.height || 0,
        layerRect?.height || 0,
        window.innerHeight,
      );
      state.layerTop = (hostRect?.top || layerRect?.top || 0) + window.scrollY;
      state.viewportHeight = viewport?.height || window.innerHeight;
      state.viewportOffsetTop = viewport?.offsetTop || 0;
      if (layer) {
        layer.style.height = `${state.height}px`;
      }
      canvas.width = Math.ceil(state.width * dpr);
      canvas.height = Math.ceil(state.height * dpr);
      canvas.style.height = `${state.height}px`;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const drawPlus = (x: number, y: number, scale: number, opacity: number) => {
      const arm = 2.3 * scale;

      context.globalAlpha = opacity;
      context.beginPath();
      context.moveTo(x - arm, y);
      context.lineTo(x + arm, y);
      context.moveTo(x, y - arm);
      context.lineTo(x, y + arm);
      context.stroke();
    };

    const draw = () => {
      const scrollY = window.scrollY;
      const viewport = window.visualViewport;
      const viewportHeight = viewport?.height || state.viewportHeight;
      const viewportTop = scrollY + (viewport?.offsetTop || state.viewportOffsetTop);
      const viewportCenterPageY = viewportTop + viewportHeight / 2;

      context.clearRect(0, 0, state.width, state.height);
      context.strokeStyle = state.color;
      context.lineCap = "round";
      context.lineWidth = 1;

      const gap = GRID_GAP;
      const centerX = state.width / 2;
      const startCol = Math.floor((-gap - centerX) / gap);
      const endCol = Math.ceil((state.width + gap - centerX) / gap);
      const topInset = -gap / 2;
      const startRow = Math.floor((-gap - topInset) / gap);
      const endRow = Math.ceil((state.height + gap - topInset) / gap);
      const influence = viewportHeight * 0.5;

      for (let row = startRow; row <= endRow; row += 1) {
        const y = topInset + row * gap;
        const pageY = state.layerTop + y;
        const distance = Math.abs(pageY - viewportCenterPageY);
        const centerWeight = 1 - clamp(distance / influence, 0, 1);
        const scale = 0.25 + centerWeight ** 2.2 * 0.6;
        const opacity = 0.07 + centerWeight * 0.12;

        for (let col = startCol; col <= endCol; col += 1) {
          drawPlus(centerX + col * gap, y, scale, opacity);
        }
      }

      context.globalAlpha = 1;
      state.frameId = 0;
    };

    const requestDraw = () => {
      if (state.frameId) return;
      state.frameId = requestAnimationFrame(draw);
    };

    const handleResize = () => {
      resizeCanvas();
      state.color = getCanvasColor();
      requestDraw();
    };

    resizeCanvas();
    draw();

    const resizeObserver = new ResizeObserver(handleResize);
    if (layerRef.current?.parentElement) {
      resizeObserver.observe(layerRef.current.parentElement);
    }

    window.addEventListener("resize", handleResize);
    window.visualViewport?.addEventListener("resize", handleResize);
    window.visualViewport?.addEventListener("scroll", requestDraw);
    window.addEventListener("scroll", requestDraw, { passive: true });

    return () => {
      if (state.frameId) cancelAnimationFrame(state.frameId);
      resizeObserver.disconnect();
      window.removeEventListener("resize", handleResize);
      window.visualViewport?.removeEventListener("resize", handleResize);
      window.visualViewport?.removeEventListener("scroll", requestDraw);
      window.removeEventListener("scroll", requestDraw);
    };
  }, []);

  return (
    <div
      ref={layerRef}
      className="pointer-events-none absolute left-0 top-0 z-0 w-full overflow-hidden"
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        className="absolute left-0 top-0 block w-full"
      />
    </div>
  );
}

export const PlusGridAnimationPage = PlusGridAnimation;
