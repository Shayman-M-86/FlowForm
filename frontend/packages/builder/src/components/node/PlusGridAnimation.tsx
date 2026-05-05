import { useEffect, useRef } from "react";

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

const GRID_GAP = 52;

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

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const state = {
      canvasY: 0,
      color: getCanvasColor(),
      frameId: 0,
      height: 0,
      layerTop: 0,
      smoothScroll: window.scrollY,
      targetScroll: window.scrollY,
      width: 0,
    };

    const resizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const layer = layerRef.current;
      const layerRect = layer?.getBoundingClientRect();

      state.width = layerRect?.width || window.innerWidth;
      state.height = window.innerHeight;
      state.layerTop = (layerRect?.top || 0) + window.scrollY;
      canvas.width = Math.ceil(state.width * dpr);
      canvas.height = Math.ceil(state.height * dpr);
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
      state.targetScroll = window.scrollY;
      const scrollDelta = state.targetScroll - state.smoothScroll;
      const scrollEase = Math.abs(scrollDelta) > 120 ? 0.9 : 0.72;

      state.smoothScroll =
        reduceMotion.matches || Math.abs(scrollDelta) < 0.5
          ? state.targetScroll
          : state.smoothScroll + scrollDelta * scrollEase;
      state.canvasY = state.smoothScroll - state.layerTop;
      canvas.style.transform = `translate3d(0, ${state.canvasY.toFixed(2)}px, 0)`;

      context.clearRect(0, 0, state.width, state.height);
      context.strokeStyle = state.color;
      context.lineCap = "round";
      context.lineWidth = 1;

      const gap = GRID_GAP;
      const centerX = state.width / 2;
      const startCol = Math.floor((-gap - centerX) / gap);
      const endCol = Math.ceil((state.width + gap - centerX) / gap);
      const topInset = -gap / 2;
      const startRow = Math.floor((state.smoothScroll - gap - topInset) / gap);
      const endRow = Math.ceil(
        (state.smoothScroll + state.height + gap - topInset) / gap,
      );
      const centerY = state.height / 2;
      const influence = state.height * 0.5;

      for (let row = startRow; row <= endRow; row += 1) {
        const pageY = topInset + row * gap;
        const y = pageY - state.smoothScroll;
        const distance = Math.abs(y - centerY);
        const centerWeight = 1 - clamp(distance / influence, 0, 1);
        const scale = 0.42 + centerWeight ** 2.2 * 0.9;
        const opacity = 0.07 + centerWeight * 0.12;

        for (let col = startCol; col <= endCol; col += 1) {
          drawPlus(centerX + col * gap, y, scale, opacity);
        }
      }

      context.globalAlpha = 1;

      if (Math.abs(state.targetScroll - state.smoothScroll) > 0.5) {
        state.frameId = requestAnimationFrame(draw);
      } else {
        state.frameId = 0;
      }
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

    window.addEventListener("resize", handleResize);
    window.addEventListener("scroll", requestDraw, { passive: true });

    return () => {
      if (state.frameId) cancelAnimationFrame(state.frameId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("scroll", requestDraw);
    };
  }, []);

  return (
    <div
      ref={layerRef}
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        className="absolute left-0 top-0 block h-screen w-full will-change-transform"
      />
    </div>
  );
}

export const PlusGridAnimationPage = PlusGridAnimation;
