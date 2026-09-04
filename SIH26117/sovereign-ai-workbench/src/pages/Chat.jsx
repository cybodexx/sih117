import { useState } from "react";
import {
  Bot,
  Send,
  Paperclip,
  ShieldCheck,
  FileText,
  ChevronDown,
  Sparkles,
} from "lucide-react";

function Chat() {
  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState([
    {
      type: "ai",
      text: "Hello! I'm Sovereign AI. I can analyze confidential industrial documents, search your internal knowledge base, and help generate business deliverables.",
    },
  ]);

  const sendMessage = () => {
    if (!message.trim()) return;

    setMessages([
      ...messages,
      {
        type: "user",
        text: message,
      },
      {
        type: "ai",
        text: "I'm currently running in demo mode. Once the backend is connected, I will process this request using the local AI models.",
      },
    ]);

    setMessage("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* Header */}
      <header className="h-20 border-b border-slate-800 flex items-center justify-between px-6 lg:px-8">

        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider">
            Workspace
          </p>

          <h1 className="text-xl font-semibold mt-1">
            AI Chat
          </h1>
        </div>

        <div className="flex items-center gap-3">

          <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-full border border-emerald-500/20 bg-emerald-500/5">

            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />

            <span className="text-sm text-emerald-400">
              Local AI
            </span>

          </div>

          <div className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center">
            L
          </div>

        </div>

      </header>


      {/* AI Model Bar */}
      <div className="px-6 lg:px-8 py-4 border-b border-slate-800">

        <div className="max-w-5xl mx-auto flex items-center justify-between">

          <div className="flex items-center gap-3">

            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <Bot
                className="text-emerald-400"
                size={21}
              />
            </div>

            <div>

              <p className="font-medium text-sm">
                Sovereign Industrial Assistant
              </p>

              <p className="text-xs text-slate-500">
                Local multimodal model
              </p>

            </div>

          </div>


          <button className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-800 hover:bg-slate-900 text-sm text-slate-400">

            Model: Industrial AI

            <ChevronDown size={15} />

          </button>

        </div>

      </div>


      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 lg:px-8 py-8">

        <div className="max-w-5xl mx-auto space-y-6">

          {messages.map((msg, index) => (

            <div
              key={index}
              className={`flex gap-4 ${
                msg.type === "user"
                  ? "justify-end"
                  : "justify-start"
              }`}
            >

              {msg.type === "ai" && (

                <div className="w-9 h-9 shrink-0 rounded-lg bg-emerald-500/10 flex items-center justify-center">

                  <Bot
                    size={18}
                    className="text-emerald-400"
                  />

                </div>

              )}


              <div
                className={`max-w-2xl rounded-2xl px-5 py-4 ${
                  msg.type === "user"
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-900 border border-slate-800 text-slate-300"
                }`}
              >

                <p className="text-sm leading-6">
                  {msg.text}
                </p>

              </div>

            </div>

          ))}

        </div>

      </div>


      {/* Suggestions */}
      <div className="px-6 lg:px-8">

        <div className="max-w-5xl mx-auto">

          <div className="flex gap-3 overflow-x-auto pb-3">

            <Suggestion
              icon={<FileText size={16} />}
              text="Analyze inspection report"
              onClick={() =>
                setMessage(
                  "Analyze the uploaded inspection report"
                )
              }
            />

            <Suggestion
              icon={<Sparkles size={16} />}
              text="Search internal SOP"
              onClick={() =>
                setMessage(
                  "Search the internal maintenance SOP"
                )
              }
            />

            <Suggestion
              icon={<FileText size={16} />}
              text="Generate approval note"
              onClick={() =>
                setMessage(
                  "Generate an approval note"
                )
              }
            />

          </div>

        </div>

      </div>


      {/* Input */}
      <div className="px-6 lg:px-8 pb-6 pt-2">

        <div className="max-w-5xl mx-auto">

          <div className="rounded-2xl border border-slate-700 bg-slate-900 p-3 focus-within:border-emerald-500/40">

            <textarea
              value={message}
              onChange={(e) =>
                setMessage(e.target.value)
              }
              onKeyDown={handleKeyDown}
              placeholder="Ask Sovereign AI anything..."
              rows="2"
              className="w-full bg-transparent outline-none resize-none text-sm text-white placeholder:text-slate-600 px-2 py-2"
            />

            <div className="flex items-center justify-between mt-2">

              <button className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition">

                <Paperclip size={18} />

                <span className="hidden sm:block text-sm">
                  Attach file
                </span>

              </button>


              <button
                onClick={sendMessage}
                className="w-10 h-10 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 flex items-center justify-center transition"
              >

                <Send size={18} />

              </button>

            </div>

          </div>


          {/* Security message */}
          <div className="flex items-center justify-center gap-2 mt-3 text-xs text-slate-600">

            <ShieldCheck size={14} />

            <span>
              Your data stays inside the organization's environment
            </span>

          </div>

        </div>

      </div>

    </div>
  );
}


function Suggestion({ icon, text, onClick }) {

  return (

    <button
      onClick={onClick}
      className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-800 bg-slate-900 hover:border-slate-700 hover:bg-slate-800 text-sm text-slate-400 transition"
    >

      {icon}

      {text}

    </button>

  );
}


export default Chat;