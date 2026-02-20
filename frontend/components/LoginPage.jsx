"use client";
import { useState } from "react";
import { KeyRound, Loader2, ArrowRight, Shield } from "lucide-react";
import useAuthStore from "../stores/authStore";

const MicrosoftLogo = () => (
  <svg width="21" height="21" viewBox="0 0 21 21" fill="none">
    <rect x="1" y="1" width="9" height="9" fill="#F25022" />
    <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
    <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
    <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
  </svg>
);

export default function LoginPage() {
  const [step, setStep] = useState("sso"); // "sso" | "email" | "password"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, loginWithSSO, isLoading, error, rememberMe, setRememberMe } = useAuthStore();

  const handleSSOLogin = () => {
    loginWithSSO();
  };

  const handleEmailSubmit = (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    useAuthStore.setState({ error: null });
    setStep("password");
  };

  const handlePasswordSubmit = (e) => {
    e.preventDefault();
    if (!password) return;
    login(email, password);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-sky-50 flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-jai-primary/5 to-transparent" />
        <div className="absolute -bottom-40 -left-40 w-[600px] h-[600px] rounded-full bg-gradient-to-tr from-sky-100/40 to-transparent" />
      </div>

      <div className="relative w-full max-w-[440px]">
        {/* Logo & branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-jai-primary to-[#C13B5F] shadow-lg shadow-jai-primary/20 mb-5">
            <Shield className="text-white" size={28} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">JAI Agent OS</h1>
          <p className="text-sm text-slate-500 mt-1">JAGGAER AI Agent Operating System</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8">
          {step === "sso" && (
            <>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">Sign in</h2>
              <p className="text-sm text-slate-500 mb-6">Choose your authentication method to continue</p>

              {/* Microsoft SSO Button */}
              <button
                onClick={handleSSOLogin}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-3 bg-white border-2 border-slate-200 rounded-xl px-4 py-3.5 text-sm font-medium text-slate-700 hover:border-slate-300 hover:bg-slate-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 size={18} className="animate-spin text-slate-400" />
                ) : (
                  <MicrosoftLogo />
                )}
                Sign in with Microsoft
              </button>
              {error && (
                <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-3">{error}</p>
              )}

              {/* Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-white px-3 text-slate-400 uppercase tracking-wider">or</span>
                </div>
              </div>

              {/* Email form */}
              <form onSubmit={handleEmailSubmit}>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Email address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@jaggaer.com"
                  autoFocus
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10 transition-all"
                />
                <button
                  type="submit"
                  disabled={!email.trim()}
                  className="mt-4 w-full flex items-center justify-center gap-2 bg-jai-primary hover:bg-jai-primary-hover text-white rounded-xl px-4 py-3 text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm shadow-jai-primary/20"
                >
                  Continue
                  <ArrowRight size={16} />
                </button>
              </form>
            </>
          )}

          {step === "password" && (
            <>
              <button
                onClick={() => setStep("sso")}
                className="text-xs text-slate-500 hover:text-slate-700 transition mb-4 flex items-center gap-1"
              >
                ← Back
              </button>
              <h2 className="text-lg font-semibold text-slate-900 mb-1">Enter password</h2>
              <p className="text-sm text-slate-500 mb-1">Signing in as</p>
              <div className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2 mb-5">
                <div className="w-7 h-7 rounded-full bg-jai-primary/10 text-jai-primary flex items-center justify-center text-xs font-semibold">
                  {email[0]?.toUpperCase()}
                </div>
                <span className="text-sm text-slate-700 font-medium truncate">{email}</span>
              </div>

              <form onSubmit={handlePasswordSubmit}>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoFocus
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-jai-primary focus:ring-2 focus:ring-jai-primary/10 transition-all"
                />
                {error && (
                  <p className="text-xs text-red-500 mt-2">{error}</p>
                )}
                <label className="flex items-center gap-2 mt-4 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-jai-primary focus:ring-jai-primary/30 accent-jai-primary cursor-pointer"
                  />
                  <span className="text-xs text-slate-600">Remember me</span>
                </label>
                <button
                  type="submit"
                  disabled={!password || isLoading}
                  className="mt-3 w-full flex items-center justify-center gap-2 bg-jai-primary hover:bg-jai-primary-hover text-white rounded-xl px-4 py-3 text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm shadow-jai-primary/20"
                >
                  {isLoading ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <>
                      Sign in
                      <KeyRound size={15} />
                    </>
                  )}
                </button>
              </form>

              <button className="mt-3 w-full text-xs text-slate-400 hover:text-jai-primary transition text-center">
                Forgot password?
              </button>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-400">
            Protected by JAGGAER Identity
          </p>
          <p className="text-[11px] text-slate-300 mt-1">
            © {new Date().getFullYear()} JAGGAER — All rights reserved
          </p>
        </div>
      </div>
    </div>
  );
}
