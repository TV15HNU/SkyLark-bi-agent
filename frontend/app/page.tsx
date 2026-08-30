"use client";

import React, { useState } from "react";
import { Header } from "./components/Header";
import { LeftRail } from "./components/LeftRail";
import { ChatThread, ChatMessage } from "./components/ChatThread";
import { RightRail } from "./components/RightRail";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [pinnedData, setPinnedData] = useState<any>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleSendMessage = async (queryText: string) => {
    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const analystMsgId = `analyst-${Date.now()}`;
    let accumulatedContent = "";
    let accumulatedTraces: string[] = [];
    let accumulatedCards: any[] = [];
    let accumulatedCaveats: string[] = [];

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: queryText,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response reader available");
      }

      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.replace("data: ", "").trim();
              if (dataStr === "[DONE]") {
                break;
              }
              try {
                const event = JSON.parse(dataStr);
                if (event.type === "thought") {
                  accumulatedTraces.push(event.content);
                } else if (event.type === "tool_start") {
                  accumulatedTraces.push(event.content);
                } else if (event.type === "tool_end") {
                  accumulatedTraces.push(event.content);
                } else if (event.type === "answer") {
                  accumulatedContent += event.content;
                } else if (event.type === "ui_card") {
                  accumulatedCards.push(event.card);
                  // Automatically pin latest structured card to RightRail
                  setPinnedData(event.card);
                } else if (event.type === "caveat") {
                  accumulatedCaveats.push(event.content);
                } else if (event.type === "error") {
                  accumulatedContent += `\n\n⚠️ Error: ${event.message}`;
                }

                // Update analyst message in state
                setMessages((prev) => {
                  const filtered = prev.filter((m) => m.id !== analystMsgId);
                  return [
                    ...filtered,
                    {
                      id: analystMsgId,
                      sender: "analyst",
                      content: accumulatedContent,
                      traces: [...accumulatedTraces],
                      cards: [...accumulatedCards],
                      caveats: [...accumulatedCaveats],
                      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                    },
                  ];
                });
              } catch (parseErr) {
                console.warn("SSE parse error:", parseErr, dataStr);
              }
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: analystMsgId,
          sender: "analyst",
          content: `⚠️ Failed to complete analysis: ${err.message || "Unknown error"}. Operating in resilient fallback mode.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPrompt = (prompt: string) => {
    handleSendMessage(prompt);
  };

  const handleSelectSector = (sector: string | null) => {
    setSelectedSector(sector);
    if (sector) {
      handleSendMessage(`Analyze sales pipeline and work order execution for ${sector} sector.`);
    }
  };

  const handleOpenLeadership = () => {
    handleSendMessage("Draft a comprehensive Q3 leadership update with top 3 strategic risks and operational KPIs");
  };

  const handleRefreshData = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top Header */}
      <Header
        onRefreshData={handleRefreshData}
        onOpenLeadership={handleOpenLeadership}
      />

      {/* Main 3-Zone Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Rail: Data Resilience & Sector Scope */}
        <LeftRail
          selectedSector={selectedSector}
          onSelectSector={handleSelectSector}
          onSelectPrompt={handleSelectPrompt}
          refreshTrigger={refreshTrigger}
        />

        {/* Center: Conversation Thread & Generative Cards */}
        <ChatThread
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onPinCard={(card) => setPinnedData(card)}
          onSelectPrompt={handleSelectPrompt}
        />

        {/* Right Rail: Pinned Intelligence & Executive Deck */}
        <RightRail
          pinnedData={pinnedData}
          onSelectPrompt={handleSelectPrompt}
        />
      </div>
    </div>
  );
}
