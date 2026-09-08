import { useState , useRef } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  Clock3,
  Loader2,
  FileText,
  Search,
  Brain,
  Code2,
  ShieldCheck,
  Database,
  Cpu,
  ChevronRight,
  Terminal,
} from "lucide-react";

function AgentWorkspace() {
  const [running, setRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(4);
  const [paused, setPaused] = useState(false);
 const timerRefs = useRef([]);
 const [logs, setLogs] = useState([]);
 const [completed, setCompleted] = useState(false);

  const steps = [
    {
      title: "Read Inspection Report",
      description: "Extracting information from the uploaded PDF",
      icon: FileText,
      status: "completed",
      time: "2.4s",
    },
    {
      title: "Run OCR & Vision Analysis",
      description: "Analyzing scanned pages and equipment images",
      icon: Search,
      status: "completed",
      time: "4.8s",
    },
    {
      title: "Search Knowledge Base",
      description: "Finding relevant SOPs and maintenance records",
      icon: Database,
      status: "completed",
      time: "1.7s",
    },
    {
      title: "Select Local AI Model",
      description: "Routing task to the best available model",
      icon: Cpu,
      status: "completed",
      time: "0.6s",
    },
    {
      title: "Analyze Findings",
      description: "Reasoning over inspection results and internal knowledge",
      icon: Brain,
      status: "running",
      time: "Running",
    },
    {
      title: "Verify Calculations",
      description: "Checking generated values using sandbox tools",
      icon: Code2,
      status: "pending",
      time: "--",
    },
    {
      title: "Generate Approval Note",
      description: "Creating the final Word document",
      icon: FileText,
      status: "pending",
      time: "--",
    },
  ];

const handleRun = () => {
  timerRefs.current.forEach((timer) => clearTimeout(timer));
  timerRefs.current = [];

  setRunning(true);
  setPaused(false);
  setCurrentStep(0);
  setCompleted(false);
    setLogs([
  "[10:42:01] Agent initialized",
  "[10:42:02] Loading Inspection_Report.pdf",
]);
  steps.forEach((_, index) => {
   const timer = setTimeout(() => {
  setCurrentStep(index + 1);

  const logMessages = [
    <div className="space-y-3">
  {logs.length === 0 ? (
    <p className="text-sm text-slate-600">
      No execution logs yet. Run the agent to begin.
    </p>
  ) : (
    
    logs.map((log, index) => (
      <div
        key={index}
        className="flex items-start gap-3 rounded-lg bg-slate-950/60 px-4 py-3"
      >
        <Terminal size={16} className="mt-0.5 text-emerald-400 shrink-0" />

        <p className="font-mono text-xs text-slate-300">
          {log}
        </p>
      </div>
    ))
  )}
</div>
    
  ];

  setLogs((prev) => [...prev, logMessages[index]]);

 if (index === steps.length - 1) {
  setRunning(false);
  setCompleted(true);
}
}, (index + 1) * 1500);

    timerRefs.current.push(timer);
  });
};
const handlePauseResume = () => {
  if (!running) return;

  if (!paused) {
    // Pause execution
    timerRefs.current.forEach((timer) => clearTimeout(timer));
    timerRefs.current = [];
    setPaused(true);
  } else {
    // Resume execution
    setPaused(false);

    const nextStep = currentStep;

    for (let index = nextStep; index < steps.length; index++) {
      const timer = setTimeout(() => {
        setCurrentStep(index + 1);

        if (index === steps.length - 1) {
          setRunning(false);
          setPaused(false);
        }
      }, (index - nextStep + 1) * 1500);

      timerRefs.current.push(timer);
    }
  }
};
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Agent Workspace</h1>
            <p className="mt-1 text-sm text-slate-400">
              Monitor and control multi-step AI agent execution
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400 sm:flex">
              <ShieldCheck size={16} />
              On-Premise AI
            </div>

            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-semibold">
              L
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="p-6">
        {/* Task */}
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-blue-400">
                Current Agent Task
              </p>

              <h2 className="text-xl font-semibold">
                Analyze Inspection Report and Generate Approval Note
              </h2>

              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                The AI agent will analyze the inspection report, search the
                internal knowledge base, verify findings and generate a final
                approval document.
              </p>
            </div>

            <button
              onClick={handleRun}
              className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-medium transition hover:bg-blue-500"
            >
              {running ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play size={18} />
                  Run Agent
                </>
              )}
            </button>
          </div>

          {/* Task info */}
          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Input</p>
              <p className="mt-1 text-sm font-medium">
                Inspection_Report.pdf
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Agent</p>
              <p className="mt-1 text-sm font-medium">Inspection Agent</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Model</p>
              <p className="mt-1 text-sm font-medium">Auto Selected</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Environment</p>
              <p className="mt-1 text-sm font-medium text-emerald-400">
                Local GPU
              </p>
            </div>
          </div>
        </section>

        {/* Execution area */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          {/* Steps */}
          <section className="xl:col-span-2 rounded-2xl border border-slate-800 bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-5">
              <div>
                <h3 className="font-semibold">Execution Plan</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Agent-generated multi-step workflow
                </p>
              </div>

              <div className="rounded-full bg-blue-500/10 px-3 py-1.5 text-xs text-blue-400">
                4 / 7 completed
              </div>
            </div>

            <div className="p-6">
              {steps.map((step, index) => {
                const Icon = step.icon;
                const stepStatus =
  currentStep > index
    ? "completed"
    : currentStep === index
    ? "running"
    : "pending";

                return (
                  <div key={index} className="flex gap-4">
                    {/* Timeline */}
                    <div className="flex flex-col items-center">
                      <div
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                          stepStatus === "completed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : stepStatus === "running"
                            ? "bg-blue-500/10 text-blue-400"
                            : "bg-slate-800 text-slate-500"
                        }`}
                      >
                        {stepStatus === "completed" ? (
                          <CheckCircle2 size={20} />
                        ) : stepStatus === "running" ? (
                          <Loader2 size={20} className="animate-spin" />
                        ) : (
                          <Icon size={20} />
                        )}
                      </div>

                      {index !== steps.length - 1 && (
                        <div
                          className={`my-1 h-10 w-px ${
                            stepStatus === "completed"
                              ? "bg-emerald-500/30"
                              : "bg-slate-800"
                          }`}
                        />
                      )}
                    </div>

                    {/* Step content */}
                    <div className="min-w-0 flex-1 pb-6">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p
                            className={`font-medium ${
                              stepStatus === "pending"
                                ? "text-slate-500"
                                : "text-white"
                            }`}
                          >
                            {step.title}
                          </p>

                          <p className="mt-1 text-xs leading-5 text-slate-500">
                            {step.description}
                          </p>
                        </div>

                        <span
                          className={`flex items-center gap-1 text-xs ${
                            step.status === "completed"
                              ? "text-emerald-400"
                              : stepStatus === "running"
                              ? "text-blue-400"
                              : "text-slate-600"
                          }`}
                        >
                          {stepStatus === "running" && (
                            <Clock3 size={13} />
                          )}
                          {step.time}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Agent status */}
          <section className="rounded-2xl border border-slate-800 bg-slate-900">
            <div className="border-b border-slate-800 px-6 py-5">
              <h3 className="font-semibold">Agent Status</h3>
              <p className="mt-1 text-xs text-slate-500">
                Runtime environment
              </p>
            </div>

            <div className="space-y-4 p-6">
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
                    <Brain size={20} />
                  </div>

                  <div>
                    <p className="text-sm font-medium">Agent Reasoning</p>
                    <p className="mt-1 text-xs text-blue-400">
                      {running ? "Executing task..." : "Ready"}
                    </p>
                  </div>
                </div>
              </div>

              <StatusItem
                icon={Cpu}
                title="Local LLM"
                value="Online"
                active
              />

              <StatusItem
                icon={Database}
                title="Knowledge Base"
                value="Connected"
                active
              />

              <StatusItem
                icon={Code2}
                title="Code Sandbox"
                value="Ready"
                active
              />

              <StatusItem
                icon={ShieldCheck}
                title="Network"
                value="Internal Only"
                active
              />

              {/* Controls */}
              <div className="border-t border-slate-800 pt-5">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500">
                  Controls
                </p>

                <div className="grid grid-cols-2 gap-3">
                 <button
onClick={handlePauseResume}
  disabled={!running}
  className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
>
  {paused ? (
    <>
      <Play size={16} />
      Resume
    </>
  ) : (
    <>
      <Pause size={16} />
      Pause
    </>
  )}
</button>

                                <button
                onClick={handleRun}
                className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
                >
                <RotateCcw size={16} />
                Restart
                </button>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Logs */}
        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900">
          <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-5">
            <Terminal size={20} className="text-slate-400" />

            <div>
              <h3 className="font-semibold">Execution Logs</h3>
              <p className="mt-1 text-xs text-slate-500">
                Real-time agent activity and tool calls
              </p>
            </div>
          </div>

          <div className="overflow-x-auto p-6">
            <div className="min-w-[650px] rounded-xl border border-slate-800 bg-black/30 p-4 font-mono text-xs leading-7">
              <p className="text-slate-500">
                [10:42:01] Agent initialized
              </p>

              <p className="text-blue-400">
                [10:42:02] Loading Inspection_Report.pdf
              </p>

              <p className="text-purple-400">
                [10:42:05] OCR tool executed locally
              </p>

              <p className="text-purple-400">
                [10:42:09] Vision analysis completed
              </p>

              <p className="text-blue-400">
                [10:42:11] Searching internal knowledge base
              </p>

              <p className="text-emerald-400">
                [10:42:13] 8 relevant documents retrieved
              </p>

              <p className="text-blue-400">
                [10:42:14] Model Router selected local Llama 3.1 70B
              </p>

              <p className="text-yellow-400">
                [10:42:16] Agent reasoning in progress...
              </p>
            </div>
          </div>
        </section>

        {/* Security */}
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <ShieldCheck
            size={20}
            className="mt-0.5 shrink-0 text-emerald-400"
          />

          <div>
            <p className="text-sm font-medium text-emerald-400">
              Secure Agent Execution
            </p>

            <p className="mt-1 text-xs leading-5 text-slate-400">
              Agent planning, model inference, document retrieval and tool
              execution occur inside the organization's on-premise
              infrastructure.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusItem({ icon: Icon, title, value, active }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
      <Icon
        size={19}
        className={active ? "text-emerald-400" : "text-slate-500"}
      />

      <div className="flex-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs text-slate-500">{value}</p>
      </div>

      {active && (
        <div className="h-2 w-2 rounded-full bg-emerald-400" />
      )}
    </div>
  );
}

export default AgentWorkspace;