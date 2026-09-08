import { useState } from "react";
import {
  ShieldCheck,
  Lock,
  Mail,
  Eye,
  EyeOff,
  Server,
  CheckCircle2,
} from "lucide-react";

export default function Login({ onLogin }) {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    // Demo login
    if (onLogin) {
      onLogin();
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center px-4 relative overflow-hidden">

      {/* Background glow */}
      <div className="absolute top-[-200px] left-[-200px] w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-[-200px] right-[-200px] w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl"></div>

      <div className="w-full max-w-md relative z-10">

        {/* Logo / Brand */}
        <div className="text-center mb-8">

          <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-600/15 border border-blue-500/30 flex items-center justify-center mb-4">
            <ShieldCheck size={34} className="text-blue-400" />
          </div>

          <h1 className="text-2xl font-bold">
            Sovereign AI Workbench
          </h1>

          <p className="text-slate-400 mt-2 text-sm">
            Secure Industrial AI Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-7 shadow-2xl backdrop-blur">

          <div className="mb-6">
            <h2 className="text-xl font-semibold">
              Welcome back
            </h2>

            <p className="text-sm text-slate-400 mt-1">
              Sign in to access your AI workspace
            </p>
          </div>

          <form onSubmit={handleSubmit}>

            {/* Email */}
            <div className="mb-5">

              <label className="block text-sm text-slate-300 mb-2">
                Email Address
              </label>

              <div className="relative">

                <Mail
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                />

                <input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                />

              </div>
            </div>

            {/* Password */}
            <div className="mb-4">

              <label className="block text-sm text-slate-300 mb-2">
                Password
              </label>

              <div className="relative">

                <Lock
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                />

                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl py-3 pl-10 pr-11 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>

              </div>
            </div>

            {/* Remember + Forgot */}
            <div className="flex items-center justify-between mb-6">

              <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">

                <input
                  type="checkbox"
                  className="accent-blue-600"
                />

                Remember me

              </label>

              <button
                type="button"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Forgot password?
              </button>

            </div>

            {/* Login Button */}
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-500 transition rounded-xl py-3 font-medium text-sm shadow-lg shadow-blue-600/20"
            >
              Sign In
            </button>

          </form>

          {/* Security Info */}
          <div className="mt-6 pt-5 border-t border-slate-800">

            <div className="flex items-center gap-3">

              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <Server size={18} className="text-emerald-400" />
              </div>

              <div>
                <p className="text-sm font-medium text-slate-200">
                  Air-Gapped Environment
                </p>

                <p className="text-xs text-slate-500">
                  All AI processing stays on-premise
                </p>
              </div>

              <CheckCircle2
                size={17}
                className="text-emerald-400 ml-auto"
              />

            </div>

          </div>

        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-600 mt-6">
          Sovereign Industrial AI Workbench • Secure Local Intelligence
        </p>

      </div>
    </div>
  );
}