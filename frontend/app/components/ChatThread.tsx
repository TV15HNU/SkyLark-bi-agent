"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  Send, 
  Terminal, 
  Sparkles, 
  ChevronDown, 
  ChevronRight, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2, 
  CornerDownLeft,
  ShieldAlert,
  ArrowRight,
  Download,
  Copy,
  Check,
  Mic,
  MicOff
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { GenerativeCard } from "./GenerativeCards";

export interface ChatMessage {
  id: string;
  sender: "user" | "analyst";
  content: string;
  traces?: string[];
  cards?: any[];
  caveats?: string[];
  timestamp: string;
}

interface ChatThreadProps {
  messages: ChatMessage[];
  onSendMessage: (query: string) => void;
  isLoading: boolean;
  onPinCard: (card: any) => void;
  onSelectPrompt: (p: string) => void;
}

export const ChatThread: React.FC<ChatThreadProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onPinCard,
  onSelectPrompt,
}) => {
  const [inputQuery, setInputQuery] = useState("");
  const [openTraces, setOpenTraces] = useState<{ [msgId: string]: boolean }>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const toggleVoiceInput = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join("");
        setInputQuery(transcript);
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Failed to start speech recognition:", err);
      setIsListening(false);
    }
  };

  const [downloadedId, setDownloadedId] = useState<string | null>(null);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDownloadMd = (msg: ChatMessage) => {
    try {
      let exportText = msg.content;
      // If message includes a rich leadership deck, export the full formatted report
      const deckCard = msg.cards?.find((c: any) => c.type === "leadership_deck");
      if (deckCard?.data?.markdown_export) {
        exportText = deckCard.data.markdown_export;
      }

      const blob = new Blob([exportText], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.setAttribute("download", `Skylark_Analyst_Report_${new Date().toISOString().slice(0, 10)}.md`);
      document.body.appendChild(a);
      a.click();

      setDownloadedId(msg.id);
      setTimeout(() => {
        setDownloadedId(null);
        if (document.body.contains(a)) {
          document.body.removeChild(a);
        }
        URL.revokeObjectURL(url);
      }, 1500);
    } catch (err) {
      console.error("Failed to download markdown file:", err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isLoading) return;
    onSendMessage(inputQuery.trim());
    setInputQuery("");
  };

  const toggleTrace = (id: string) => {
    setOpenTraces((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const starterChips = [
    {
      label: "⚡ Energy Sector Pipeline",
      query: "How is our pipeline looking for the energy sector this quarter?",
      desc: "Resolves Mining + Renewables + Powerline and surfaces probability caveats"
    },
    {
      label: "⚙️ Unbilled Work Orders",
      query: "What is our total unbilled amount and collection risk across ongoing work orders?",
      desc: "Reconciles 5 overlapping status fields into authoritative financial metrics"
    },
    {
      label: "🔗 Won Deals Missing Work Orders",
      query: "Which deals are won in sales pipeline but have no work order created in operations?",
      desc: "Cross-board lifecycle audit surfacing 113 won deals needing setup"
    },
    {
      label: "🚁 Draft Leadership Brief",
      query: "Draft a comprehensive Q3 leadership update with top 3 strategic risks",
      desc: "Generates 1-click exportable executive Markdown brief"
    },
    {
      label: "🛡️ Data Quality & Caveats Audit",
      query: "Show completeness score and all active data resilience caveats across boards",
      desc: "Deep audit of 74% unpopulated probability and missing dates"
    }
  ];

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] bg-background overflow-hidden">
      
      {/* 1. MESSAGE LIST */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        
        {/* First-load Empty State */}
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto py-8 space-y-6">
            <div className="border border-border bg-card/70 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-accent-sky/10 border border-accent-sky/30 flex items-center justify-center text-accent-sky">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-text-primary uppercase tracking-wide">
                    Skylark Business Intelligence Agent
                  </h2>
                  <p className="text-xs text-text-secondary">
                    Real-time founder queries across Monday.com Deals & Work Orders boards
                  </p>
                </div>
              </div>

              <div className="text-xs text-text-secondary leading-relaxed pt-1 border-t border-border/60">
                <p>
                  This agent queries live operational and sales pipeline data, performs defensive normalization 
                  (duplicate header pruning, 5-to-1 status reconciliation, unit extraction), and explicitly surfaces data-quality caveats.
                </p>
              </div>
            </div>

            {/* Suggested Founder Prompts */}
            <div className="space-y-2">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-accent-sky" />
                <span>Founder-Level Inquiry Starters</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {starterChips.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectPrompt(chip.query)}
                    className="p-3 rounded-lg border border-border bg-card hover:bg-card-hover hover:border-accent-sky/40 text-left transition-all group flex flex-col justify-between space-y-1"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-text-primary text-xs group-hover:text-accent-sky transition-colors">
                        {chip.label}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-text-muted group-hover:text-accent-sky group-hover:translate-x-0.5 transition-all" />
                    </div>
                    <p className="text-[11px] text-text-muted group-hover:text-text-secondary transition-colors">
                      {chip.desc}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Conversation Items */}
        {messages.map((msg) => {
          const isUser = msg.sender === "user";

          if (isUser) {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-xl bg-card border border-border rounded-lg px-3.5 py-2 text-xs text-text-primary font-medium flex items-center space-x-2 shadow-sm">
                  <span className="font-mono-data text-accent-sky font-bold text-[11px]">&gt;</span>
                  <span>{msg.content}</span>
                </div>
              </div>
            );
          }

          // Analyst Turn
          return (
            <div key={msg.id} className="max-w-3xl space-y-3">
              
              {/* Tool Execution Reasoning Pills */}
              {msg.traces && msg.traces.length > 0 && (
                <div className="text-xs">
                  <button
                    onClick={() => toggleTrace(msg.id)}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-panel hover:bg-card border border-border text-[11px] text-text-muted hover:text-text-secondary transition-colors font-mono-data"
                  >
                    <span className="text-accent-sky font-bold">⚡</span>
                    <span>Multi-step Agent Reasoning ({msg.traces.length} steps)</span>
                    {openTraces[msg.id] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </button>

                  {openTraces[msg.id] && (
                    <div className="mt-1.5 p-2.5 rounded bg-panel/90 border border-border font-mono-data text-[10px] space-y-1 text-text-secondary">
                      {msg.traces.map((trace, i) => (
                        <div key={i} className="flex items-start space-x-1.5">
                          <span className="text-accent-sky shrink-0">•</span>
                          <span>{trace}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Analyst Prose Response */}
              <div className="analyst-note-border py-1">
                <div className="text-xs sm:text-sm text-text-primary leading-relaxed space-y-2 prose prose-invert max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ node, ...props }) => <h1 className="text-base font-bold text-text-primary mt-3 mb-2 border-b border-border/60 pb-1" {...props} />,
                      h2: ({ node, ...props }) => <h2 className="text-sm font-bold text-accent-sky mt-3 mb-1.5 flex items-center space-x-1.5" {...props} />,
                      h3: ({ node, ...props }) => <h3 className="text-xs font-bold text-accent-sky uppercase tracking-wider mt-2.5 mb-1" {...props} />,
                      p: ({ node, ...props }) => <p className="mb-2 leading-relaxed text-text-primary text-xs sm:text-[13px]" {...props} />,
                      strong: ({ node, ...props }) => <strong className="font-semibold text-text-primary text-accent-sky/90" {...props} />,
                      ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1 my-2 text-text-secondary text-xs sm:text-[13px]" {...props} />,
                      ol: ({ node, ...props }) => <ol className="list-decimal list-inside space-y-1 my-2 text-text-secondary text-xs sm:text-[13px]" {...props} />,
                      li: ({ node, ...props }) => <li className="leading-relaxed pl-1" {...props} />,
                      table: ({ node, ...props }) => (
                        <div className="overflow-x-auto my-3 rounded-lg border border-border/80 bg-card/60">
                          <table className="w-full text-left text-xs border-collapse font-sans" {...props} />
                        </div>
                      ),
                      thead: ({ node, ...props }) => <thead className="bg-panel/80 border-b border-border text-[11px] font-semibold text-text-secondary uppercase tracking-wider" {...props} />,
                      th: ({ node, ...props }) => <th className="px-3 py-2 border-r border-border/40 last:border-r-0 font-medium" {...props} />,
                      td: ({ node, ...props }) => <td className="px-3 py-2 border-b border-border/40 last:border-b-0 border-r last:border-r-0 border-border/40 text-text-primary font-mono-data text-xs" {...props} />,
                      blockquote: ({ node, ...props }) => <blockquote className="border-l-2 border-accent-sky/40 pl-3 py-1 my-2 italic text-xs text-text-secondary bg-panel/40 rounded-r" {...props} />,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {/* Inline Caveat Chips */}
                {msg.caveats && msg.caveats.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {msg.caveats.map((cav, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-accent-amber/10 border border-accent-amber/30 text-[11px] text-accent-amber flex items-start space-x-1.5 font-medium"
                      >
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <span>{cav}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Inline Generative UI Cards */}
                {msg.cards && msg.cards.length > 0 && (
                  <div className="mt-3 space-y-3">
                    {msg.cards.map((card, idx) => (
                      <div key={idx} className="relative group">
                        <GenerativeCard card={card} onPinToRail={onPinCard} />
                      </div>
                    ))}
                  </div>
                )}

                {/* Footer Source Marker & Action Buttons */}
                <div className="mt-2.5 pt-2 border-t border-border/40 text-[10px] font-mono-data text-text-muted flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span>source: monday.com live query</span>
                    <span>•</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  <div className="flex items-center space-x-2 font-sans">
                    <button
                      onClick={() => handleCopy(msg.id, msg.content)}
                      className="px-2.5 py-1 rounded bg-panel hover:bg-card border border-border text-text-secondary hover:text-text-primary transition-colors flex items-center space-x-1.5 text-[10px] font-medium"
                      title="Copy response as Markdown"
                    >
                      {copiedId === msg.id ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-accent-emerald" />
                          <span className="text-accent-emerald font-semibold">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-text-muted" />
                          <span>Copy MD</span>
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleDownloadMd(msg)}
                      className="px-2.5 py-1 rounded bg-accent-sky/20 hover:bg-accent-sky/30 border border-accent-sky/40 text-accent-sky transition-colors flex items-center space-x-1.5 text-[10px] font-semibold shadow-sm"
                      title="Download this response as a .md file"
                    >
                      {downloadedId === msg.id ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-accent-emerald" />
                          <span className="text-accent-emerald font-semibold">Downloaded!</span>
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5 text-accent-sky" />
                          <span>Download .md</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

            </div>
          );
        })}

        {/* Loading Spinner / Skeleton State */}
        {isLoading && (
          <div className="max-w-3xl space-y-2 analyst-note-border py-1">
            <div className="flex items-center space-x-2 text-accent-sky text-xs font-mono-data">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Querying monday.com GraphQL API & executing multi-step reasoning...</span>
            </div>
            <div className="w-full h-12 bg-panel/60 rounded-lg animate-pulse border border-border" />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 2. COMMAND INPUT BAR */}
      <div className="p-3.5 border-t border-border bg-panel">
        <form onSubmit={handleSubmit} className="relative max-w-4xl mx-auto flex items-center">
          <div className="absolute left-3.5 text-accent-sky font-mono-data font-bold text-sm">
            &gt;
          </div>
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={
              isListening 
                ? "🎙️ Listening... Speak your founder query now" 
                : "Ask founder query (e.g. 'How is pipeline looking for energy sector this quarter?')"
            }
            disabled={isLoading}
            className={`w-full pl-8 pr-20 py-2.5 bg-card hover:bg-card-hover focus:bg-card border ${
              isListening 
                ? "border-accent-rose shadow-[0_0_12px_rgba(244,63,94,0.25)] ring-1 ring-accent-rose" 
                : "border-border focus:border-accent-sky"
            } rounded-lg text-xs sm:text-sm text-text-primary placeholder:text-text-muted focus:outline-none transition-all`}
          />
          <div className="absolute right-2 flex items-center space-x-1">
            <button
              type="button"
              onClick={toggleVoiceInput}
              disabled={isLoading}
              title={isListening ? "Stop listening" : "Click to speak your query (Voice Input)"}
              className={`p-1.5 rounded-md transition-all ${
                isListening
                  ? "bg-accent-rose/20 text-accent-rose animate-pulse border border-accent-rose/60"
                  : "bg-panel hover:bg-card text-text-muted hover:text-accent-sky border border-border"
              }`}
            >
              {isListening ? <MicOff className="w-4 h-4 text-accent-rose" /> : <Mic className="w-4 h-4" />}
            </button>
            <button
              type="submit"
              disabled={!inputQuery.trim() || isLoading}
              className="p-1.5 rounded-md bg-accent-sky/10 hover:bg-accent-sky/20 text-accent-sky disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
              title="Send query"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
        <div className="text-[10px] text-text-muted text-center mt-1.5 font-mono-data flex items-center justify-center space-x-2">
          {isListening ? (
            <span className="text-accent-rose font-medium animate-pulse flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-rose" />
              <span>Voice recording active · Click mic or stop speaking to submit</span>
            </span>
          ) : (
            <span>Press Enter to query live monday.com boards · Never hardcoded CSVs</span>
          )}
        </div>
      </div>

    </div>
  );
};
