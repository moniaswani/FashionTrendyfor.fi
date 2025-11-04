import React, { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

export function Chatbot() {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom whenever messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed) return; // prevent empty input

    const newMessage = { role: "user", text: trimmed };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(
        "https://5ns3sodc1b.execute-api.eu-west-2.amazonaws.com/default/chatbot",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: trimmed }),
        }
      );
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.answer || "No answer received." }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, there was an error fetching a response." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-semibold mb-4 text-gray-800">AI Fashion Chatbot</h2>

      <div className="space-y-4 h-96 overflow-y-auto border p-4 mb-4 rounded-lg bg-gray-50">
        {messages.map((m, idx) => (
          <div key={idx} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block px-4 py-2 rounded-lg ${
                m.role === "user"
                  ? "bg-green-600 text-white"
                  : "bg-gray-200 text-gray-800"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && <p className="text-gray-500 text-sm">Thinking...</p>}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex items-center space-x-2">
        <input
          className="flex-grow border rounded-lg p-2"
          placeholder="Ask about colors, materials, trends..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={loading}
        />
        <button
          className={`p-2 rounded-lg ${loading ? "bg-gray-400" : "bg-green-600 text-white"}`}
          onClick={handleSend}
          disabled={loading}
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
