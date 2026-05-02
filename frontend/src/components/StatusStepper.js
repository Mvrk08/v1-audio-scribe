import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

const steps = ["idle", "recording", "uploading", "processing", "completed"];

export const StatusStepper = ({ state }) => {
  const activeIndex = steps.indexOf(state === "running" ? "processing" : state);
  const failed = state === "failed";

  return (
    <div className="status-strip" data-testid="processing-status-indicator">
      {steps.map((step, index) => {
        const active = index === activeIndex;
        const done = index < activeIndex || state === "completed";
        return (
          <div className="status-item" key={step} data-testid={`status-step-${step}`}>
            {failed && index === activeIndex ? (
              <XCircle className="h-4 w-4 text-[#B0413E]" aria-hidden="true" />
            ) : active && state !== "completed" ? (
              <Loader2 className="h-4 w-4 animate-spin text-[#4A7C9D]" aria-hidden="true" />
            ) : done ? (
              <CheckCircle2 className="h-4 w-4 text-[#3D7A5D]" aria-hidden="true" />
            ) : (
              <Circle className="h-4 w-4 text-[#A8AAA5]" aria-hidden="true" />
            )}
            <span>{step}</span>
          </div>
        );
      })}
    </div>
  );
};
