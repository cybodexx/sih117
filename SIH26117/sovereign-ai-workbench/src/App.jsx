import { useState } from "react";
import Chat from "./pages/Chat";
import Documents from "./pages/Documents";
import KnowledgeBase from "./pages/KnowledgeBase";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import AgentWorkspace from "./pages/AgentWorkspace";
import Login from "./pages/Login";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Brain,
  BarChart3,
  SettingsIcon,
  ShieldCheck,
  Menu,
  X,
  Activity,
  Database,
  Cpu,
  ArrowUpRight,
 LogOut,
} from "lucide-react";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [page, setPage] = useState("Dashboard");
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const menuItems = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "AI Chat", icon: MessageSquare },
    { name: "Documents", icon: FileText },
    { name: "Knowledge Base", icon: Brain },
    { name: "Reports", icon: BarChart3 },
    { name: "Agent Workspace", icon: Brain },
    { name: "Settings", icon: SettingsIcon },
  ];
  if (!isLoggedIn) {
  return <Login onLogin={() => setIsLoggedIn(true)} />;
}

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* Mobile Header */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-emerald-400" size={25} />
          <span className="font-bold">Sovereign AI</span>
        </div>

        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-lg hover:bg-slate-800"
        >
          {sidebarOpen ? <X /> : <Menu />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`
          fixed left-0 top-0 z-40 h-screen w-64
          bg-slate-900 border-r border-slate-800
          transition-transform duration-300
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
          lg:translate-x-0
        `}
      >

        {/* Logo */}
        <div className="h-20 flex items-center px-6 border-b border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center mr-3">
            <ShieldCheck className="text-emerald-400" size={24} />
          </div>

          <div>
            <h1 className="font-bold text-lg">Sovereign AI</h1>
            <p className="text-xs text-slate-500">Industrial Workbench</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                onClick={() => setPage(item.name)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3
                  rounded-xl text-sm transition
                  ${
                    item.name === page
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }
                `}
              >
                <Icon size={19} />
                {item.name}
              </button>
            );
          })}
        </nav>

        {/* Security Card */}
        <div className="absolute bottom-5 left-4 right-4">
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              <span className="text-sm font-semibold text-emerald-400">
                System Secure
              </span>
            </div>

            <p className="text-xs text-slate-500">
              Running completely on-premise
            </p>
          </div>
        </div>
      </aside>

      {/* Main Area */}
      <main className="lg:ml-64 min-h-screen">
        {page === "AI Chat" ? (
  <Chat />
  ) : page === "Documents" ? (
    <Documents />
  ) : page === "Knowledge Base" ? (
    <KnowledgeBase />
  ) : page === "Reports" ? (
    <Reports />
  ) : page === "Settings" ? (
   <Settings />
  ) : page === "Agent Workspace" ? (
  <AgentWorkspace />
) : (
  <>

        {/* Top Navbar */}
        <header className="hidden lg:flex h-20 border-b border-slate-800 items-center justify-between px-8 bg-slate-950">

          <div>
            <p className="text-sm text-slate-500">Workspace</p>
            <h2 className="font-semibold text-lg">
              Industrial AI Dashboard
            </h2>
          </div>

          <div className="flex items-center gap-4">

            {/* Local Status */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-emerald-500/20 bg-emerald-500/5">
              <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
              <span className="text-sm text-emerald-400">
                AI System Local
              </span>
            </div>

            {/* User */}
            {/* User + Logout */}
<div className="flex items-center gap-3">

  <div className="flex items-center gap-3">
    <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-semibold">
      L
    </div>

    <div className="hidden xl:block">
      <p className="text-sm font-medium">
        Lavkush Nishad
      </p>
      <p className="text-xs text-slate-500">
        AI Workbench User
      </p>
    </div>
  </div>

  <button
    onClick={() => setIsLoggedIn(false)}
    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition"
    title="Logout"
  >
    <LogOut size={17} />
    <span className="hidden xl:inline">Logout</span>
  </button>

</div>

          </div>
        </header>

        {/* Dashboard Content */}
        <section className="p-6 lg:p-8">

          {/* Welcome */}
          <div className="mb-8">
            <p className="text-emerald-400 text-sm mb-2">
              Welcome back
            </p>

            <h1 className="text-3xl lg:text-4xl font-bold">
              Sovereign AI Workbench
            </h1>

            <p className="text-slate-500 mt-2 max-w-2xl">
              Analyze confidential industrial data, run AI agents and
              generate real business deliverables — completely on-premise.
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">

            <StatCard
              title="AI Models"
              value="04"
              subtitle="Available locally"
              icon={<Cpu size={22} />}
            />

            <StatCard
              title="Documents"
              value="128"
              subtitle="In knowledge base"
              icon={<FileText size={22} />}
            />

            <StatCard
              title="AI Tasks"
              value="24"
              subtitle="Completed this week"
              icon={<Activity size={22} />}
            />

            <StatCard
              title="Data Transfer"
              value="0 MB"
              subtitle="External transfer"
              icon={<ShieldCheck size={22} />}
            />

          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

            {/* Quick Actions */}
            <div className="xl:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">

              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-lg font-semibold">
                    Quick Actions
                  </h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Start your next AI task
                  </p>
                </div>

                <ArrowUpRight className="text-slate-600" />
              </div>

              <div className="grid sm:grid-cols-2 gap-4">

                <ActionCard
                  icon={<MessageSquare />}
                  title="Start AI Chat"
                  description="Ask questions and analyze information"
                  onClick={() => setPage("AI Chat")}
                />

                <ActionCard
                  icon={<FileText />}
                  title="Analyze Document"
                  description="Upload PDF, image or report"
                   onClick={() => setPage("Documents")}
                />

                <ActionCard
                  icon={<Brain />}
                  title="Search Knowledge"
                  description="Query internal SOPs and manuals"
                  onClick={() => setPage("Knowledge Base")}
                />

                <ActionCard
                  icon={<BarChart3 />}
                  title="Generate Report"
                  description="Create Word, Excel or PPT output"
                   onClick={() => setPage("Reports")}
                />

              </div>
            </div>

            {/* System Status */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">

              <h2 className="text-lg font-semibold mb-6">
                System Status
              </h2>

              <StatusItem
                icon={<Cpu size={18} />}
                title="Local AI Models"
                status="Running"
              />

              <StatusItem
                icon={<Database size={18} />}
                title="Knowledge Base"
                status="Connected"
              />

              <StatusItem
                icon={<ShieldCheck size={18} />}
                title="Network Isolation"
                status="Active"
              />

              <StatusItem
                icon={<Activity size={18} />}
                title="Agent Runtime"
                status="Ready"
              />

              <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800">
                <p className="text-xs text-slate-500">
                  Security
                </p>

                <p className="text-sm text-emerald-400 font-medium mt-1">
                  ✓ No external API connection
                </p>
              </div>

            </div>

          </div>

          {/* Recent Activity */}
          <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">

            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-lg font-semibold">
                  Recent AI Activity
                </h2>

                <p className="text-sm text-slate-500 mt-1">
                  Latest tasks performed by the workbench
                </p>
              </div>
            </div>

            <ActivityRow
              title="Inspection Report Analysis"
              description="Inspection_Report_2026.pdf"
              time="2 minutes ago"
              status="Completed"
            />

            <ActivityRow
              title="SOP Knowledge Search"
              description="Maintenance SOP Database"
              time="18 minutes ago"
              status="Completed"
            />

            <ActivityRow
              title="Approval Note Generation"
              description="Plant Maintenance Recommendation"
              time="42 minutes ago"
              status="Completed"
            />

          </div>
                  </section>
      </>
    )}
  </main>
        
    </div>
  );
}


/* ---------- Components ---------- */

function StatCard({ title, value, subtitle, icon }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 hover:border-slate-700 transition">

      <div className="flex justify-between items-start">

        <div>
          <p className="text-sm text-slate-500">{title}</p>

          <p className="text-3xl font-bold mt-2">
            {value}
          </p>

          <p className="text-xs text-slate-600 mt-1">
            {subtitle}
          </p>
        </div>

        <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-emerald-400">
          {icon}
        </div>

      </div>
    </div>
  );
}

function ActionCard({ icon, title, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="text-left p-5 rounded-xl border border-slate-800 bg-slate-950 hover:border-emerald-500/30 hover:bg-slate-900 transition"
    >

      <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-4">
        {icon}
      </div>

      <h3 className="font-medium">
        {title}
      </h3>

      <p className="text-sm text-slate-500 mt-1">
        {description}
      </p>

    </button>
  );
}


function StatusItem({ icon, title, status }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800">

      <div className="flex items-center gap-3">
        <div className="text-slate-400">
          {icon}
        </div>

        <span className="text-sm text-slate-300">
          {title}
        </span>
      </div>

      <span className="text-xs text-emerald-400">
        {status}
      </span>

    </div>
  );
}


function ActivityRow({ title, description, time, status }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-4 border-b border-slate-800 last:border-0">

      <div className="flex items-center gap-4">

        <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center">
          <Activity size={18} className="text-emerald-400" />
        </div>

        <div>
          <p className="font-medium text-sm">
            {title}
          </p>

          <p className="text-xs text-slate-500 mt-1">
            {description}
          </p>
        </div>

      </div>

      <div className="flex items-center gap-4 text-xs">

        <span className="text-slate-600">
          {time}
        </span>

        <span className="text-emerald-400">
          ● {status}
        </span>

      </div>

    </div>
  );
}

export default App;