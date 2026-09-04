import { GripVertical } from "lucide-react";
import { useState, type KeyboardEvent, type PointerEvent } from "react";

type ResizeHandleProps = {
  width: number;
  minWidth: number;
  maxWidth: number;
  onResize: (width: number) => void;
};

const KEYBOARD_STEP = 24;

export function ResizeHandle({ width, minWidth, maxWidth, onResize }: ResizeHandleProps) {
  const [dragging, setDragging] = useState(false);

  function startResize(event: PointerEvent<HTMLDivElement>): void {
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  function resize(event: PointerEvent<HTMLDivElement>): void {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }
    onResize(clamp(window.innerWidth - event.clientX, minWidth, maxWidth));
  }

  function stopResize(event: PointerEvent<HTMLDivElement>): void {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    setDragging(false);
    // Mouse click leaves :focus on the handle; that kept the lime "active" styles stuck.
    if (event.type !== "lostpointercapture") {
      event.currentTarget.blur();
    }
  }

  function resizeWithKeyboard(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      onResize(clamp(width + KEYBOARD_STEP, minWidth, maxWidth));
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      onResize(clamp(width - KEYBOARD_STEP, minWidth, maxWidth));
    }
  }

  const active = dragging
    ? "bg-lime border-lime/60 text-lime opacity-100"
    : "bg-line border-line text-mute opacity-60 group-hover:bg-lime group-hover:border-lime/60 group-hover:text-lime group-hover:opacity-100 group-focus-visible:bg-lime group-focus-visible:border-lime/60 group-focus-visible:text-lime group-focus-visible:opacity-100";

  return (
    <div
      role="separator"
      aria-label="Resize code panel"
      aria-orientation="vertical"
      aria-valuemin={minWidth}
      aria-valuemax={maxWidth}
      aria-valuenow={width}
      tabIndex={0}
      title="Drag to resize code panel"
      className="group relative hidden w-3 shrink-0 touch-none cursor-col-resize bg-transparent focus:outline-none lg:block"
      onPointerDown={startResize}
      onPointerMove={resize}
      onPointerUp={stopResize}
      onPointerCancel={stopResize}
      onLostPointerCapture={stopResize}
      onKeyDown={resizeWithKeyboard}
    >
      <span
        className={`absolute inset-y-0 left-1/2 w-px -translate-x-1/2 transition-colors ${
          dragging ? "bg-lime" : "bg-line group-hover:bg-lime group-focus-visible:bg-lime"
        }`}
      />
      <span
        className={`absolute left-1/2 top-1/2 z-10 grid h-10 w-5 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-md border bg-panel shadow-lg transition-all ${active}`}
      >
        <GripVertical className="h-3 w-3" aria-hidden="true" />
      </span>
    </div>
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
