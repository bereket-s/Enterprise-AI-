"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Send, Sparkles, User } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Card } from "./ui";

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

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-3.5 py-2.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse-dot"
          style={{ animationDelay: `${i * 0.16}s` }}
        />
      ))}
    </div>
  );
}

export function CopilotWidget() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [history, loading]);

  const ask = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setQuestion("");
    try {
      const resp = await api.post("/api/copilot/ask", { question: q });
      setHistory((h) => [...h, { question: q, answer: resp.data.answer }]);
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
    <Card icon={Sparkles} title="AI Business Copilot" noAnimate className="animate-fade-in-up">
      <div ref={scrollRef} className="space-y-4 max-h-80 overflow-y-auto mb-3 pr-1">
        {history.length === 0 && !loading && (
          <p className="text-sm text-slate-500 py-2">
            Ask a question about your business data, or try one of the suggestions below.
          </p>
        )}
        <AnimatePresence initial={false}>
          {history.map((entry, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-2"
            >
              <div className="flex items-start gap-2 justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand-600 text-white px-3.5 py-2 text-sm shadow-soft">
                  {entry.question}
                </div>
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-500">
                  <User size={13} />
                </span>
              </div>
              <div className="flex items-start gap-2">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-white">
                  <Bot size={13} />
                </span>
                <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-slate-100 text-slate-700 px-3.5 py-2 text-sm">
                  {entry.answer}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-white">
              <Bot size={13} />
            </span>
            <div className="rounded-2xl rounded-tl-sm bg-slate-100">
              <TypingDots />
            </div>
          </motion.div>
        )}
      </div>

      {error && (
        <div className="mb-3">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      <form onSubmit={onSubmit} className="flex gap-2 mb-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask the Copilot..."
          className="flex-1 rounded-full border border-slate-300 px-4 py-2 text-sm transition-shadow focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          aria-label="Send"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition-all hover:bg-brand-700 disabled:opacity-50 active:scale-95"
        >
          <Send size={15} />
        </button>
      </form>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => ask(s)}
            disabled={loading}
            className="text-xs rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-600 hover:bg-brand-50 hover:border-brand-200 hover:text-brand-700 transition-colors disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>
    </Card>
  );
}
