import { Check } from 'lucide-react';

const STAGES = [
  'Capturing',
  'Recording',
  'Transcribing',
  'Analyzing',
  'Generating',
  'Speaking',
];

interface PipelineProgressProps {
  activeStage: number;
}

export function PipelineProgress({ activeStage }: PipelineProgressProps) {
  if (activeStage < 0) return null;

  return (
    <div className="pipeline-progress">
      {STAGES.map((stage, index) => {
        const isDone = index < activeStage;
        const isActive = index === activeStage;

        return (
          <div key={stage} style={{ display: 'contents' }}>
            <div className={`pipeline-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}>
              <span className="pipeline-step-icon">
                {isDone ? <Check size={12} /> : index + 1}
              </span>
              <span>{stage}</span>
            </div>
            {index < STAGES.length - 1 && (
              <div className={`pipeline-connector ${isDone ? 'done' : ''}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
