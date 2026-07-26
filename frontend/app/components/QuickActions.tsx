"use client";

interface QuickActionsProps {
  onActionClick: (question: string) => void;
}

const actions = [
  {
    label: "Summarize Key Points",
    question: "Summarize the key points from both videos",
  },
  {
    label: "Compare Metadata",
    question: "Compare the metadata and engagement metrics of both videos",
  },
  {
    label: "Extract Code Snippets",
    question: "Extract any code snippets or technical details mentioned",
  },
  {
    label: "Sentiment Analysis",
    question: "Analyze the sentiment and tone of both videos",
  },
];

export default function QuickActions({ onActionClick }: QuickActionsProps) {
  return (
    <div className="flex gap-2 mb-3 overflow-x-auto pb-1 scrollbar-hide">
      {actions.map((action) => (
        <button
          key={action.label}
          onClick={() => onActionClick(action.question)}
          className="px-4 py-2 bg-white border border-surface-200 hover:border-accent-300 hover:bg-accent-50 rounded-full text-xs font-medium text-surface-700 transition-all whitespace-nowrap flex-shrink-0"
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}