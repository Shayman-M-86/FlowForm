import { useEffect, useRef } from "react";

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

    const draw = () => {
      const layer = layerRef.current;
      const host = layer?.parentElement;
      const hostRect = host?.getBoundingClientRect();
      const layerRect = layer?.getBoundingClientRect();

      const width = hostRect?.width || layerRect?.width || window.innerWidth;
      const height = Math.max(
        host?.scrollHeight || 0,
        hostRect?.height || 0,
        layerRect?.height || 0,
        window.innerHeight,
      );

      if (layer) layer.style.height = `${height}px`;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.ceil(width * dpr);
      canvas.height = Math.ceil(height * dpr);
      canvas.style.height = `${height}px`;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);

      context.clearRect(0, 0, width, height);
      context.strokeStyle = getCanvasColor();
      context.lineCap = "round";
      context.lineWidth = 1;

      const gap = GRID_GAP;
      const arm = 2.3;
      const centerX = width / 2;
      const topInset = -gap / 2;
      const startCol = Math.floor((-gap - centerX) / gap);
      const endCol = Math.ceil((width + gap - centerX) / gap);
      const startRow = Math.floor((-gap - topInset) / gap);
      const endRow = Math.ceil((height + gap - topInset) / gap);

      const fadeZone = gap * 9;
      for (let row = startRow; row <= endRow; row++) {
        const y = topInset + row * gap;
        const distFromEdge = Math.min(y, height - y);
        const edgeWeight = Math.min(distFromEdge / fadeZone, 1);
        const rowScale = 0.25 + edgeWeight ** 2.2 * 0.75;
        const rowOpacity = (0.07 + edgeWeight * 0.06) * rowScale;
        const rowArm = arm * rowScale;
        context.globalAlpha = rowOpacity;
        for (let col = startCol; col <= endCol; col++) {
          const x = centerX + col * gap;
          context.beginPath();
          context.moveTo(x - rowArm, y);
          context.lineTo(x + rowArm, y);
          context.moveTo(x, y - rowArm);
          context.lineTo(x, y + rowArm);
          context.stroke();
        }
      }
      context.globalAlpha = 1;
    };

    draw();

    const resizeObserver = new ResizeObserver(draw);
    if (layerRef.current?.parentElement) {
      resizeObserver.observe(layerRef.current.parentElement);
    }
    window.addEventListener("resize", draw);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", draw);
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
