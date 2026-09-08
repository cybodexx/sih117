import { useState } from "react";
import {
  Cpu,
  ShieldCheck,
  HardDrive,
  Network,
  Bell,
  User,
  Save,
  CheckCircle2,
  Lock,
  Server,
} from "lucide-react";

function Settings() {
  const [model, setModel] = useState("Llama 3.1 70B");
  const [notifications, setNotifications] = useState(true);
  const [autoSelect, setAutoSelect] = useState(true);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="mt-1 text-sm text-slate-400">
              Configure your sovereign AI workbench
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400 sm:flex">
              <ShieldCheck size={16} />
              System Secure
            </div>

            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-semibold">
              L
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="p-6">
        {/* AI Model Configuration */}
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">
                <Cpu size={22} />
              </div>

              <div>
                <h2 className="font-semibold">AI Model Configuration</h2>
                <p className="text-sm text-slate-500">
                  Configure local open-weight AI models
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-6 p-6">
            {/* Default Model */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Default AI Model
              </label>

              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-blue-500 md:w-2/3"
              >
                <option>Llama 3.1 70B</option>
                <option>Qwen 2.5 72B</option>
                <option>Mistral Large</option>
                <option>Vision-Language Model</option>
              </select>

              <p className="mt-2 text-xs text-slate-500">
                Models are hosted and executed inside the local GPU server.
              </p>
            </div>

            {/* Auto Model Selection */}
            <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 p-4">
              <div>
                <p className="font-medium">Automatic Model Selection</p>
                <p className="mt-1 text-xs text-slate-500">
                  Automatically choose the best local model for each task.
                </p>
              </div>

              <button
                onClick={() => setAutoSelect(!autoSelect)}
                className={`relative h-6 w-11 rounded-full transition ${
                  autoSelect ? "bg-blue-600" : "bg-slate-700"
                }`}
              >
                <span
                  className={`absolute top-1 h-4 w-4 rounded-full bg-white transition ${
                    autoSelect ? "left-6" : "left-1"
                  }`}
                />
              </button>
            </div>
          </div>
        </section>

        {/* Security */}
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-emerald-500/10 p-3 text-emerald-400">
                <ShieldCheck size={22} />
              </div>

              <div>
                <h2 className="font-semibold">Security & Privacy</h2>
                <p className="text-sm text-slate-500">
                  Sovereign data protection configuration
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 p-6 md:grid-cols-2">
            {/* Air Gap */}
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
              <div className="flex items-center gap-3">
                <Network className="text-emerald-400" size={22} />

                <div>
                  <p className="font-medium">Air-Gapped Environment</p>
                  <p className="mt-1 text-xs text-slate-500">
                    External network access is disabled.
                  </p>
                </div>

                <CheckCircle2
                  className="ml-auto text-emerald-400"
                  size={20}
                />
              </div>
            </div>

            {/* Local Processing */}
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
              <div className="flex items-center gap-3">
                <Lock className="text-emerald-400" size={22} />

                <div>
                  <p className="font-medium">Local Data Processing</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Documents never leave the organization.
                  </p>
                </div>

                <CheckCircle2
                  className="ml-auto text-emerald-400"
                  size={20}
                />
              </div>
            </div>
          </div>
        </section>

        {/* System Configuration */}
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-purple-500/10 p-3 text-purple-400">
                <Server size={22} />
              </div>

              <div>
                <h2 className="font-semibold">System Configuration</h2>
                <p className="text-sm text-slate-500">
                  Local infrastructure status
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 p-6 md:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
              <HardDrive className="mb-3 text-blue-400" size={22} />
              <p className="text-sm text-slate-400">Storage</p>
              <p className="mt-1 font-semibold">2.4 TB Available</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
              <Cpu className="mb-3 text-purple-400" size={22} />
              <p className="text-sm text-slate-400">GPU Server</p>
              <p className="mt-1 font-semibold">Online</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5">
              <Network className="mb-3 text-emerald-400" size={22} />
              <p className="text-sm text-slate-400">Network</p>
              <p className="mt-1 font-semibold text-emerald-400">
                Internal Only
              </p>
            </div>
          </div>
        </section>

        {/* Notifications */}
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900">
          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-yellow-500/10 p-3 text-yellow-400">
                <Bell size={22} />
              </div>

              <div>
                <p className="font-semibold">Notifications</p>
                <p className="mt-1 text-sm text-slate-500">
                  Receive alerts when AI tasks are completed.
                </p>
              </div>
            </div>

            <button
              onClick={() => setNotifications(!notifications)}
              className={`relative h-6 w-11 rounded-full transition ${
                notifications ? "bg-blue-600" : "bg-slate-700"
              }`}
            >
              <span
                className={`absolute top-1 h-4 w-4 rounded-full bg-white transition ${
                  notifications ? "left-6" : "left-1"
                }`}
              />
            </button>
          </div>
        </section>

        {/* User Profile */}
        <section className="mb-6 rounded-2xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-slate-800 p-3 text-slate-300">
                <User size={22} />
              </div>

              <div>
                <h2 className="font-semibold">User Profile</h2>
                <p className="text-sm text-slate-500">
                  Current workbench account
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-5 p-6 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm text-slate-400">
                Name
              </label>

              <input
                value="Lavkush Nishad"
                readOnly
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm text-slate-400">
                Role
              </label>

              <input
                value="AI Workbench User"
                readOnly
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none"
              />
            </div>
          </div>
        </section>

        {/* Save */}
        <div className="flex justify-end">
          <button className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-medium transition hover:bg-blue-500">
            <Save size={18} />
            Save Settings
          </button>
        </div>

        {/* Security Footer */}
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <ShieldCheck
            size={20}
            className="mt-0.5 shrink-0 text-emerald-400"
          />

          <div>
            <p className="text-sm font-medium text-emerald-400">
              Sovereign AI Environment
            </p>

            <p className="mt-1 text-xs leading-5 text-slate-400">
              Configuration, AI models, documents and user data are managed
              within the organization's private infrastructure.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Settings;