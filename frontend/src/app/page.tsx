"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  ShieldCheck, AlertTriangle, FileText, CheckCircle2, XCircle, 
  HelpCircle, UploadCloud, RefreshCw, Cpu, Layers,
  Search, Download, ExternalLink, Info, Copy, Check, Activity,
  Fingerprint, Eye, Binary, Sliders, Database, ArrowRight,
  History, Lock, User, Clock, HardDrive, Key
} from "lucide-react";
import { supabase, isSupabaseConfigured } from "../lib/supabase";

interface MLModelResult {
  model_name: string;
  model_version: string;
  architecture?: string;
  specialization?: string;
  known_limitation?: string;
  predicted_label: string;
  confidence: number;
  execution_time_ms: number;
  raw_probabilities: Record<string, number>;
  normalized_probabilities?: Record<string, number>;
}

interface AnalysisData {
  id: string;
  user_id?: string;
  image_sha256: string;
  image_phash: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  dimensions_width: number;
  dimensions_height: number;
  storage_path?: string;
  report_storage_path?: string;
  signed_image_url?: string;
  signed_report_url?: string;
  final_verdict: string;
  overall_confidence: number;
  verdict_reasons: string[];
  limitations: string[];
  status: string;
  engine_version: string;
  created_at: string;
  forensic_signals?: {
    exif_metadata: Record<string, any>;
    has_ai_metadata: boolean;
    ai_metadata_tags: string[];
    c2pa_manifest_detected: boolean;
    ela_mean_discrepancy: number;
    ela_max_discrepancy: number;
    ela_anomaly_detected: boolean;
    ela_heatmap_url: string;
    ela_storage_path?: string;
    fft_peak_harmonic_ratio: number;
    fft_lattice_anomaly_detected: boolean;
    fft_spectrum_url: string;
    fft_storage_path?: string;
    noise_variance: number;
    noise_uniformity_score: number;
    compression_quality_estimate: number;
    steganography_anomaly: boolean;
  };
  ml_evaluations?: MLModelResult[];
  content_dna?: {
    sha256_hash: string;
    md5_hash: string;
    perceptual_hash: string;
    difference_hash: string;
    wavelet_hash: string;
    dna_fingerprint_composite: string;
  };
}

export default function DetectiveDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState<string>("");
  const [result, setResult] = useState<AnalysisData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "ml" | "ela" | "fft" | "metadata" | "history">("overview");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [exifFilter, setExifFilter] = useState("");

  // Investigation History
  const [historyList, setHistoryList] = useState<AnalysisData[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Authenticated user session
  const [user, setUser] = useState<any>(null);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const ACCEPTED_EXTENSIONS = /\.(jpe?g|png|webp|gif|bmp|tiff?|avif|heic|heif|ico|jfif)$/i;

  // Supabase Auth listener
  useEffect(() => {
    if (supabase) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        setUser(session?.user ?? null);
      });

      const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setUser(session?.user ?? null);
      });

      return () => subscription.unsubscribe();
    }
  }, []);

  // Fetch investigation history
  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const headers: Record<string, string> = {};
      if (supabase) {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          headers["Authorization"] = `Bearer ${session.access_token}`;
        }
      }

      const res = await fetch(`${API_BASE}/api/v1/detect/history?limit=30`, { headers });
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [user]);

  const handleFileSelect = (selectedFile: File) => {
    const byMime = selectedFile.type.startsWith("image/");
    const byExt = ACCEPTED_EXTENSIONS.test(selectedFile.name);
    if (!byMime && !byExt) {
      setError("Please select a valid image file (JPEG, PNG, WebP, GIF, BMP, TIFF, AVIF, HEIC).");
      return;
    }
    setError(null);
    setFile(selectedFile);
    setResult(null);
    setPreviewUrl(URL.createObjectURL(selectedFile));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setProgressStep("Sanitizing upload & validating image stream...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      setTimeout(() => setProgressStep("Auditing EXIF headers & C2PA manifest boxes..."), 400);
      setTimeout(() => setProgressStep("Computing Error Level Analysis & 2D FFT spectral lattice..."), 1000);
      setTimeout(() => setProgressStep("Executing neural SigLIP + Swin + ViT ensemble inference..."), 1800);
      setTimeout(() => setProgressStep("Persisting to PostgreSQL & uploading to private storage..."), 2600);

      const headers: Record<string, string> = {};
      if (supabase) {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          headers["Authorization"] = `Bearer ${session.access_token}`;
        }
      }

      const res = await fetch(`${API_BASE}/api/v1/detect/analyze`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Analysis request failed.");
      }

      const data = await res.json();
      setResult(data);
      fetchHistory(); // refresh investigation history
    } catch (err: any) {
      setError(err.message || "Failed to analyze image.");
    } finally {
      setLoading(false);
      setProgressStep("");
    }
  };

  const handleLoadPastInvestigation = (item: AnalysisData) => {
    setResult(item);
    setFile(null);
    if (item.signed_image_url) {
      setPreviewUrl(item.signed_image_url);
    } else {
      setPreviewUrl(null);
    }
    setActiveTab("overview");
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) return;
    setAuthLoading(true);
    setAuthError(null);
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: authEmail,
        password: authPassword,
      });
      if (error) throw error;
      setShowAuthModal(false);
      setAuthPassword("");
    } catch (err: any) {
      setAuthError(err.message || "Sign in failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleSignUp = async () => {
    if (!supabase) return;
    setAuthLoading(true);
    setAuthError(null);
    try {
      const { error } = await supabase.auth.signUp({
        email: authEmail,
        password: authPassword,
      });
      if (error) throw error;
      alert("Sign up successful! Please check your email for confirmation or log in.");
    } catch (err: any) {
      setAuthError(err.message || "Sign up failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleSignOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
      setUser(null);
    }
  };

  const copyToClipboard = (text: string, keyName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyName);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const getVerdictTheme = (verdict: string) => {
    switch (verdict) {
      case "REAL / HUMAN":
        return { 
          badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
          cardBorder: "border-emerald-500/40",
          glow: "from-emerald-500/20 via-transparent to-transparent",
          icon: CheckCircle2,
          tag: "GENUINE OPTICAL CAPTURE",
          accentColor: "text-emerald-400"
        };
      case "AI-GENERATED":
        return { 
          badge: "bg-rose-500/10 text-rose-400 border-rose-500/30",
          cardBorder: "border-rose-500/40",
          glow: "from-rose-500/20 via-transparent to-transparent",
          icon: XCircle,
          tag: "SYNTHETIC GENERATIVE MEDIA",
          accentColor: "text-rose-400"
        };
      case "AI-MODIFIED":
        return { 
          badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          cardBorder: "border-amber-500/40",
          glow: "from-amber-500/20 via-transparent to-transparent",
          icon: AlertTriangle,
          tag: "HYBRID / PARTIAL INPAINTING",
          accentColor: "text-amber-400"
        };
      case "MANIPULATED":
        return { 
          badge: "bg-purple-500/10 text-purple-400 border-purple-500/30",
          cardBorder: "border-purple-500/40",
          glow: "from-purple-500/20 via-transparent to-transparent",
          icon: AlertTriangle,
          tag: "DIGITAL SPLICING / COMPOSITE",
          accentColor: "text-purple-400"
        };
      case "INCONCLUSIVE — MODEL DISAGREEMENT":
        return { 
          badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
          cardBorder: "border-amber-500/40",
          glow: "from-amber-500/20 via-transparent to-transparent",
          icon: AlertTriangle,
          tag: "MODEL DISAGREEMENT / OOD",
          accentColor: "text-amber-400"
        };
      default:
        return { 
          badge: "bg-slate-500/10 text-slate-400 border-slate-500/30",
          cardBorder: "border-slate-700",
          glow: "from-slate-500/10 via-transparent to-transparent",
          icon: HelpCircle,
          tag: "INDETERMINATE EVIDENCE",
          accentColor: "text-slate-400"
        };
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Professional Telemetry Bar */}
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 text-cyan-400 shadow-sm shadow-cyan-950">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-slate-100">
                  AI Content-Origin Detective
                </h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800/60 text-cyan-400 font-semibold">
                  v1.0.0 FORENSIC ENGINE
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Multi-Signal Neural Ensemble & Digital Forensics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            {/* Supabase Auth State */}
            {isSupabaseConfigured ? (
              user ? (
                <div className="flex items-center gap-2 text-xs">
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300">
                    <User className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="truncate max-w-[140px]">{user.email}</span>
                  </div>
                  <button
                    onClick={handleSignOut}
                    className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 text-xs transition"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="px-3.5 py-1.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Investigator Login</span>
                </button>
              )
            ) : (
              <div className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                <HardDrive className="w-3.5 h-3.5 text-slate-600" />
                <span>Persistent DB Ready</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-8">
        {error && (
          <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-900/60 text-rose-300 flex items-start gap-3 text-xs leading-relaxed">
            <AlertTriangle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
            <div className="flex-1">
              <span className="font-bold">Investigation Alert: </span>
              {error}
            </div>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 text-xs font-mono">
              Dismiss
            </button>
          </div>
        )}

        {/* Upload & Evidence Input Section */}
        {!result ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Primary Forensic Ingestion Dropzone */}
            <div className="lg:col-span-7 space-y-4">
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-3xl p-8 sm:p-12 text-center transition cursor-pointer flex flex-col items-center justify-center min-h-[360px] bg-slate-900/20 hover:bg-slate-900/40 ${
                  file ? "border-cyan-500/60 bg-cyan-950/10" : "border-slate-800 hover:border-slate-700"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,.heic,.avif,.webp"
                  className="hidden"
                  onChange={(e) => e.target.files && e.target.files[0] && handleFileSelect(e.target.files[0])}
                />

                {previewUrl ? (
                  <div className="space-y-4 w-full">
                    <div className="relative mx-auto w-48 h-48 rounded-2xl overflow-hidden border border-slate-700/80 shadow-2xl bg-slate-950">
                      <img src={previewUrl} alt="Upload preview" className="w-full h-full object-contain" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-slate-200 truncate max-w-xs mx-auto">
                        {file?.name}
                      </p>
                      <p className="text-xs font-mono text-slate-500">
                        {file && `${(file.size / (1024 * 1024)).toFixed(2)} MB • ${file.type || "Auto-detect"}`}
                      </p>
                    </div>
                    <p className="text-[11px] text-cyan-400/80 font-mono">Click or drop to select different media</p>
                  </div>
                ) : (
                  <div className="space-y-4 max-w-sm">
                    <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-center text-cyan-400 shadow-inner">
                      <UploadCloud className="w-7 h-7" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-200">
                        Drop Media Asset for Origin Attribution
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        Raw binary ingestion preserves authentic file headers, EXIF/C2PA tags, and photon noise.
                      </p>
                    </div>
                    <div className="pt-2 flex flex-wrap justify-center gap-1.5 text-[11px] font-mono text-slate-500">
                      <span className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-800">JPEG</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-800">PNG</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-800">WebP</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-800">TIFF</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-800">AVIF</span>
                      <span className="px-2 py-0.5 rounded bg-slate-800/60 border border-slate-800">HEIC</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <button
                onClick={handleAnalyze}
                disabled={!file || loading}
                className="w-full py-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm tracking-wide shadow-lg shadow-cyan-950/50 disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                    <span>{progressStep || "Executing Investigation Pipeline..."}</span>
                  </>
                ) : (
                  <>
                    <Activity className="w-4 h-4" />
                    <span>Execute Multi-Signal Forensic Analysis</span>
                  </>
                )}
              </button>
            </div>

            {/* Right Column: Recent Investigation History */}
            <div className="lg:col-span-5 space-y-4">
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-slate-200">
                    <History className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-sm font-bold">Investigation History</h3>
                  </div>
                  <button
                    onClick={fetchHistory}
                    disabled={loadingHistory}
                    className="text-xs text-slate-400 hover:text-cyan-400 transition flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${loadingHistory ? "animate-spin" : ""}`} />
                    <span>Refresh</span>
                  </button>
                </div>

                <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                  {historyList.length > 0 ? (
                    historyList.map((item) => {
                      const theme = getVerdictTheme(item.final_verdict);
                      return (
                        <div
                          key={item.id}
                          onClick={() => handleLoadPastInvestigation(item)}
                          className="p-3 rounded-xl bg-slate-950/80 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 cursor-pointer transition space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-300 truncate max-w-[180px]">
                              {item.file_name}
                            </span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${theme.badge}`}>
                              {item.final_verdict}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                            <span>{(item.overall_confidence * 100).toFixed(0)}% Conf</span>
                            <span className="truncate max-w-[120px]">{new Date(item.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-center py-8 text-xs text-slate-500">
                      No prior investigations recorded yet.
                    </div>
                  )}
                </div>
              </div>

              {/* Forensic Standards Card */}
              <div className="p-6 rounded-2xl bg-slate-900/20 border border-slate-800/60 space-y-3 text-xs">
                <h4 className="font-bold text-slate-300 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Forensic Architecture & Standards
                </h4>
                <div className="space-y-1.5 text-slate-400 leading-relaxed">
                  <p>• <b>No Fabricated Confidence:</b> Calibrated multi-signal consensus without artificial certainty.</p>
                  <p>• <b>Neural Ensemble:</b> SigLIP + Swin Transformers fine-tuned for modern generative models.</p>
                  <p>• <b>Sensor Optics:</b> PRNU photon noise & EXIF hardware consistency audit.</p>
                  <p>• <b>Frequency Domain:</b> 2D Fourier transform deconvolution lattice spike detection.</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Detailed Forensic Dossier View */
          <div className="space-y-8 animate-fadeIn">
            {/* Top Navigation & Actions */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => { setResult(null); setFile(null); setPreviewUrl(null); }}
                  className="px-3.5 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl transition flex items-center gap-1.5"
                >
                  <ArrowRight className="w-3.5 h-3.5 rotate-180" />
                  <span>New Investigation</span>
                </button>
                <div className="text-xs font-mono text-slate-400">
                  Case ID: <span className="text-slate-200">{result.id.slice(0, 13)}...</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={`${API_BASE}/api/v1/report/${result.id}/pdf`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 text-xs font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-xl transition flex items-center gap-2"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Forensic PDF Dossier</span>
                </a>
              </div>
            </div>

            {/* Verdict Hero Banner */}
            {(() => {
              const theme = getVerdictTheme(result.final_verdict);
              const VerdictIcon = theme.icon;
              return (
                <div className={`p-6 sm:p-8 rounded-3xl bg-slate-900/50 border ${theme.cardBorder} relative overflow-hidden`}>
                  <div className={`absolute -right-20 -top-20 w-80 h-80 rounded-full blur-3xl bg-gradient-to-br ${theme.glow} pointer-events-none`} />

                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2.5">
                        <span className={`text-[11px] font-mono font-bold px-3 py-1 rounded-full border ${theme.badge}`}>
                          {theme.tag}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          {new Date(result.created_at).toUTCString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <VerdictIcon className={`w-8 h-8 ${theme.accentColor}`} />
                        <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-100">
                          {result.final_verdict}
                        </h2>
                      </div>
                      <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
                        {result.verdict_reasons[0] || "Multi-signal synthesis completed across physical optical, spectral, and machine learning models."}
                      </p>
                    </div>

                    <div className="flex flex-col items-start lg:items-end justify-center p-5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
                      <span className="text-xs text-slate-400 font-mono uppercase tracking-wider">
                        Calibrated Origin Confidence
                      </span>
                      <div className="flex items-center gap-4 w-full lg:w-60">
                        <div className="flex-1 h-3 rounded-full bg-slate-950/80 border border-slate-800 overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full transition-all duration-700" 
                            style={{ width: `${Math.round(result.overall_confidence * 100)}%` }}
                          />
                        </div>
                        <span className="text-2xl font-black font-mono text-slate-100">
                          {(result.overall_confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* 5-Pillar Forensic Signal Matrix */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Signal 1: Metadata & C2PA */}
              <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-[11px] font-mono uppercase">1. Metadata & C2PA</span>
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-base font-bold text-slate-200">
                  {result.forensic_signals?.has_ai_metadata || result.forensic_signals?.c2pa_manifest_detected ? (
                    <span className="text-rose-400">AI Manifests Found</span>
                  ) : (
                    <span className="text-slate-300">Standard / Clean</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500">
                  {result.forensic_signals?.c2pa_manifest_detected ? "C2PA Claim Detected" : "No C2PA Box Attached"}
                </p>
              </div>

              {/* Signal 2: ELA Discrepancy */}
              <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-[11px] font-mono uppercase">2. Error Level (ELA)</span>
                  <Eye className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-base font-bold text-slate-200">
                  {result.forensic_signals?.ela_anomaly_detected ? (
                    <span className="text-amber-400">Localized Discrepancy</span>
                  ) : (
                    <span className="text-emerald-400">Uniform Compression</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500">
                  Mean: {result.forensic_signals?.ela_mean_discrepancy} • Max: {result.forensic_signals?.ela_max_discrepancy}
                </p>
              </div>

              {/* Signal 3: 2D FFT Harmonics */}
              <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-[11px] font-mono uppercase">3. Spectral FFT</span>
                  <Binary className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-base font-bold text-slate-200">
                  {result.forensic_signals?.fft_lattice_anomaly_detected ? (
                    <span className="text-rose-400">Lattice Spikes</span>
                  ) : (
                    <span className="text-emerald-400">Natural Decay</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500">
                  Harmonic Ratio: {result.forensic_signals?.fft_peak_harmonic_ratio}
                </p>
              </div>

              {/* Signal 4: Sensor Noise Residual */}
              <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-[11px] font-mono uppercase">4. Sensor Noise</span>
                  <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-base font-bold text-slate-200">
                  {(result.forensic_signals?.noise_variance ?? 0) < 0.8 ? (
                    <span className="text-rose-400">Suppressed Floor</span>
                  ) : (
                    <span className="text-emerald-400">Physical PRNU</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500">
                  Variance: {result.forensic_signals?.noise_variance}
                </p>
              </div>

              {/* Signal 5: Neural Ensemble */}
              <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-[11px] font-mono uppercase">5. Neural Ensemble</span>
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-base font-bold text-slate-200">
                  {result.ml_evaluations?.some(m => m.predicted_label === "AI-GENERATED") ? (
                    <span className="text-rose-400">AI Traces Observed</span>
                  ) : (
                    <span className="text-emerald-400">Camera / Organic</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500">
                  {result.ml_evaluations?.length ?? 0} Architectures Polled
                </p>
              </div>
            </div>

            {/* Cryptographic Content DNA Bar */}
            {result.content_dna && (
              <div className="p-6 rounded-3xl bg-slate-900/30 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Fingerprint className="w-4 h-4 text-cyan-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Cryptographic Content DNA & Digital Hashes
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">Immutable File Identity</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 block text-[10px] uppercase">SHA-256 (Canonical)</span>
                    <span className="text-slate-300 break-all text-[11px]">{result.content_dna.sha256_hash}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 block text-[10px] uppercase">Perceptual Hash (pHash)</span>
                    <span className="text-slate-300 text-[11px]">{result.content_dna.perceptual_hash}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 block text-[10px] uppercase">Difference Hash (dHash)</span>
                    <span className="text-slate-300 text-[11px]">{result.content_dna.difference_hash}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 block text-[10px] uppercase">Wavelet Hash (wHash)</span>
                    <span className="text-slate-300 text-[11px]">{result.content_dna.wavelet_hash}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Interactive Investigation Tabs Navigation */}
            <div className="flex border-b border-slate-800 gap-2 overflow-x-auto pb-px">
              {[
                { id: "overview", label: "Evidentiary Audit", icon: FileText },
                { id: "ml", label: "Neural Ensemble", icon: Cpu },
                { id: "ela", label: "Error Level Analysis", icon: Eye },
                { id: "fft", label: "Spectral FFT Lattice", icon: Binary },
                { id: "metadata", label: "EXIF & C2PA", icon: Database },
                { id: "history", label: "Investigation History", icon: History }
              ].map((tab) => {
                const TabIcon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`px-4 py-3 text-xs font-semibold border-b-2 transition flex items-center gap-2 whitespace-nowrap ${
                      activeTab === tab.id
                        ? "border-cyan-400 text-cyan-400 bg-cyan-950/10"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <TabIcon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* TAB 1: EVIDENTIARY AUDIT */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-4">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Corroborating Evidentiary Findings
                  </h4>
                  <ul className="space-y-3 text-xs text-slate-300">
                    {result.verdict_reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                        <span className="text-cyan-400 font-bold mt-0.5">•</span>
                        <span className="leading-relaxed">{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-4">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Limitations & Investigation Caveats
                  </h4>
                  <ul className="space-y-3 text-xs text-slate-400">
                    {result.limitations.length > 0 ? (
                      result.limitations.map((l, i) => (
                        <li key={i} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                          <span className="text-amber-400 font-bold mt-0.5">•</span>
                          <span className="leading-relaxed">{l}</span>
                        </li>
                      ))
                    ) : (
                      <li className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-slate-500">
                        No critical evidentiary degradation detected.
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            )}

            {/* TAB 2: NEURAL ENSEMBLE */}
            {activeTab === "ml" && (
              <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-6">
                <div>
                  <h3 className="text-sm font-bold text-slate-200">Machine Learning Neural Ensemble Breakdown</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Independent vision transformer architectures evaluate visual representations, digital artistic styles, and latent diffusion traces.
                  </p>
                </div>
                <div className="grid gap-4">
                  {result.ml_evaluations && result.ml_evaluations.length > 0 ? (
                    result.ml_evaluations.map((m, i) => {
                      const isAI = m.predicted_label === "AI-GENERATED";
                      return (
                        <div key={i} className="p-5 rounded-2xl bg-slate-950 border border-slate-800/90 space-y-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-bold text-slate-200">{m.model_name}</span>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
                                  {m.model_version}
                                </span>
                              </div>
                              {m.architecture && (
                                <p className="text-[11px] text-slate-400 font-mono mt-0.5">Architecture: {m.architecture}</p>
                              )}
                              {m.specialization && (
                                <p className="text-[11px] text-slate-400 font-mono mt-0.5">Specialization: {m.specialization}</p>
                              )}
                              {m.known_limitation && (
                                <p className="text-[11px] text-slate-400 font-mono mt-0.5">Limitation: {m.known_limitation}</p>
                              )}
                              {m.normalized_probabilities && (
                                <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                                  Normalized: AI {Math.round((m.normalized_probabilities['AI-GENERATED'] ?? 0) * 100)}% / Human {Math.round((m.normalized_probabilities['REAL / HUMAN'] ?? 0) * 100)}%
                                </p>
                              )}
                              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                                Inference Latency: {m.execution_time_ms} ms
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-mono font-bold px-3 py-1 rounded-full border ${
                                isAI 
                                  ? "bg-rose-500/10 text-rose-400 border-rose-500/30" 
                                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              }`}>
                                {m.predicted_label} ({(m.confidence * 100).toFixed(1)}%)
                              </span>
                            </div>
                          </div>

                          {/* Raw Probabilities Bar */}
                          <div className="space-y-1">
                            <div className="flex justify-between text-[11px] font-mono text-slate-400">
                              <span>Probability Breakdown:</span>
                              <span>{Object.entries(m.raw_probabilities).map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`).join(" • ")}</span>
                            </div>
                            <div className="h-2 rounded-full bg-slate-900 overflow-hidden flex">
                              {Object.entries(m.raw_probabilities).map(([k, v], idx) => {
                                const isAiKey = ["ai", "artificial", "fake"].includes(k.toLowerCase());
                                return (
                                  <div
                                    key={idx}
                                    style={{ width: `${Math.round(v * 100)}%` }}
                                    className={isAiKey ? "bg-rose-500" : "bg-emerald-500"}
                                  />
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-8 rounded-2xl bg-slate-950 border border-slate-800 text-center text-slate-500 text-xs">
                      No active neural models reported evaluation.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: ELA */}
            {activeTab === "ela" && result.forensic_signals && (
              <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-200">Error Level Analysis (ELA) Heatmap</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Measures difference against fixed 95% JPEG re-quantization. Inconsistent error levels reveal regional inpainting or splicing.
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-mono">
                    <span className="text-slate-400">Mean: <b className="text-slate-200">{result.forensic_signals.ela_mean_discrepancy}</b></span>
                    <span className="text-slate-400">Max: <b className="text-slate-200">{result.forensic_signals.ela_max_discrepancy}</b></span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <span className="text-xs font-mono text-slate-400">Original Asset</span>
                    <img 
                      src={result.signed_image_url || previewUrl!} 
                      alt="Original" 
                      className="w-full h-80 object-contain rounded-2xl border border-slate-800 bg-slate-950" 
                    />
                  </div>
                  <div className="space-y-2">
                    <span className="text-xs font-mono text-slate-400">Amplified ELA Discrepancy Map</span>
                    <img 
                      src={`${API_BASE}${result.forensic_signals.ela_heatmap_url}`} 
                      alt="ELA Map" 
                      className="w-full h-80 object-contain rounded-2xl border border-slate-800 bg-slate-950" 
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: FFT */}
            {activeTab === "fft" && result.forensic_signals && (
              <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-200">2D Fourier Transform (FFT) Power Spectrum</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Identifies periodic lattice harmonics produced by neural upsampling deconvolution operations.
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-mono">
                    <span className="text-slate-400">Harmonic Ratio: <b className="text-slate-200">{result.forensic_signals.fft_peak_harmonic_ratio}</b></span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <span className="text-xs font-mono text-slate-400">Original Asset</span>
                    <img 
                      src={result.signed_image_url || previewUrl!} 
                      alt="Original" 
                      className="w-full h-80 object-contain rounded-2xl border border-slate-800 bg-slate-950" 
                    />
                  </div>
                  <div className="space-y-2">
                    <span className="text-xs font-mono text-slate-400">High-Frequency Magnitude Spectrum</span>
                    <img 
                      src={`${API_BASE}${result.forensic_signals.fft_spectrum_url}`} 
                      alt="FFT Spectrum" 
                      className="w-full h-80 object-contain rounded-2xl border border-slate-800 bg-slate-950" 
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 5: EXIF & C2PA */}
            {activeTab === "metadata" && result.forensic_signals && (
              <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-200">EXIF & Cryptographic Provenance Headers</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Audits metadata for generative parameters, Adobe/C2PA claim assertions, and camera sensor tags.
                    </p>
                  </div>
                  <input
                    type="text"
                    placeholder="Filter metadata tags..."
                    value={exifFilter}
                    onChange={(e) => setExifFilter(e.target.value)}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500/80 w-full sm:w-64"
                  />
                </div>

                {result.forensic_signals.ai_metadata_tags && result.forensic_signals.ai_metadata_tags.length > 0 && (
                  <div className="p-4 rounded-2xl bg-rose-950/20 border border-rose-900/40 space-y-2">
                    <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">Identified AI Signatures</span>
                    <div className="flex flex-wrap gap-2">
                      {result.forensic_signals.ai_metadata_tags.map((tag, idx) => (
                        <span key={idx} className="px-2.5 py-1 rounded-lg bg-rose-950/60 border border-rose-800/80 text-[11px] font-mono text-rose-300">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="max-h-96 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950 p-4 text-xs font-mono space-y-1.5">
                  {Object.entries(result.forensic_signals.exif_metadata)
                    .filter(([k, v]) => !exifFilter || k.toLowerCase().includes(exifFilter.toLowerCase()) || String(v).toLowerCase().includes(exifFilter.toLowerCase()))
                    .map(([k, v]) => (
                      <div key={k} className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-900 py-1.5 gap-2">
                        <span className="text-slate-500 font-semibold">{k}:</span>
                        <span className="text-slate-300 break-all">{String(v)}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* TAB 6: INVESTIGATION HISTORY */}
            {activeTab === "history" && (
              <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <History className="w-4 h-4 text-cyan-400" />
                    All Stored Investigations
                  </h3>
                  <span className="text-xs font-mono text-slate-500">
                    {historyList.length} total investigations stored
                  </span>
                </div>

                <div className="grid gap-3">
                  {historyList.map((item) => {
                    const theme = getVerdictTheme(item.final_verdict);
                    return (
                      <div
                        key={item.id}
                        onClick={() => handleLoadPastInvestigation(item)}
                        className="p-4 rounded-2xl bg-slate-950 border border-slate-800 hover:border-slate-700 cursor-pointer transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2.5">
                            <span className="text-xs font-bold text-slate-200">{item.file_name}</span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${theme.badge}`}>
                              {item.final_verdict}
                            </span>
                          </div>
                          <p className="text-[11px] font-mono text-slate-500">
                            SHA-256: {item.image_sha256 ? `${item.image_sha256.slice(0, 16)}...` : "N/A"} • Dimensions: {item.dimensions_width}x{item.dimensions_height} px
                          </p>
                        </div>
                        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
                          <span>{(item.overall_confidence * 100).toFixed(1)}% Conf</span>
                          <span className="text-slate-500">{new Date(item.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Supabase Investigator Auth Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 max-w-md w-full space-y-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-200">
                <Lock className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold">Investigator Authentication</h3>
              </div>
              <button
                onClick={() => setShowAuthModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs font-mono"
              >
                Close
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Authenticate via Supabase to associate investigations with your user profile, enable private asset storage, and enforce Row Level Security.
            </p>

            {authError && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-900/60 text-rose-300 text-xs">
                {authError}
              </div>
            )}

            <form onSubmit={handleSignIn} className="space-y-4">
              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="analyst@forensics.agency"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={authLoading}
                  className="flex-1 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition disabled:opacity-50"
                >
                  {authLoading ? "Authenticating..." : "Sign In"}
                </button>
                <button
                  type="button"
                  onClick={handleSignUp}
                  disabled={authLoading}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition disabled:opacity-50"
                >
                  Sign Up
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
