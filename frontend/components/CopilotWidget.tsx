"use client";

import { FormEvent, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton } from "./ui";

interface ChatEntry {
  question: string;
  answer: string;
}

const SUGGESTIONS = [
  "Why did our revenue decline?",
  "What are our top products?",
  "Which products are most likely to run out?",
  "Show me the highest-risk transactions",
  "Which machines should we inspect first?",
  "Which department needs attention?",
  "What is our revenue forecast for next month?",
  "Are we on track to hit our goals?",
];

export function CopilotWidget() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post("/api/copilot/ask", { question: q });
      setHistory((h) => [...h, { question: q, answer: resp.data.answer }]);
      setQuestion("");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ask(question);
  };

  return (
    <Card title="AI Business Copilot">
      <div className="space-y-3 max-h-72 overflow-y-auto mb-3">
        {history.length === 0 && (
          <p className="text-sm text-slate-500">
            Ask a question about your business data, or try one of the suggestions below.
          </p>
        )}
        {history.map((entry, i) => (
          <div key={i} className="text-sm">
            <p className="font-medium text-slate-800">You: {entry.question}</p>
            <p className="text-slate-600 mt-0.5">{entry.answer}</p>
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      <form onSubmit={onSubmit} className="flex gap-2 mb-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask the Copilot..."
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <PrimaryButton type="submit" disabled={loading}>
          {loading ? "Thinking..." : "Ask"}
        </PrimaryButton>
      </form>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => ask(s)}
            className="text-xs rounded-full border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-100"
          >
            {s}
          </button>
        ))}
      </div>
    </Card>
  );
}
