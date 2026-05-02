import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, Clipboard, Download, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { StatusStepper } from "@/components/StatusStepper";

const blankPrescription = { symptoms: [], diagnosis: "", medications: [], advice: [], follow_up: "" };

const arrayToText = (value) => (Array.isArray(value) ? value.join("\n") : value || "");
const textToArray = (value) => value.split("\n").map((item) => item.trim()).filter(Boolean);

export default function ResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState("processing");
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({ raw_transcript: "", translated_text: "", structured_prescription: blankPrescription });

  useEffect(() => {
    let interval;
    const load = async () => {
      try {
        const statusResponse = await api.getStatus(id);
        setStatus(statusResponse.data.status === "running" ? "processing" : statusResponse.data.status);
        if (statusResponse.data.status === "completed") {
          const resultResponse = await api.getResult(id);
          setResult(resultResponse.data);
          setForm({
            raw_transcript: resultResponse.data.raw_transcript,
            translated_text: resultResponse.data.translated_text,
            structured_prescription: resultResponse.data.structured_prescription,
          });
          clearInterval(interval);
        }
        if (statusResponse.data.status === "failed") clearInterval(interval);
      } catch (error) {
        toast.error(error.response?.data?.detail || "Could not load result");
      }
    };
    load();
    interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [id]);

  const setPrescriptionField = (field, value, isArray = false) => {
    setForm((current) => ({
      ...current,
      structured_prescription: { ...current.structured_prescription, [field]: isArray ? textToArray(value) : value },
    }));
  };

  const save = async () => {
    try {
      const response = await api.updateResult(id, form);
      setResult(response.data);
      toast.success("Edits saved");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Save failed");
    }
  };

  const download = () => {
    const p = form.structured_prescription;
    const content = `Transcript\n${form.raw_transcript}\n\nTranslation\n${form.translated_text}\n\nPrescription\nSymptoms: ${arrayToText(p.symptoms)}\nDiagnosis: ${p.diagnosis}\nMedications: ${arrayToText(p.medications)}\nAdvice: ${arrayToText(p.advice)}\nFollow-up: ${p.follow_up}`;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `medical-session-${id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const copy = async () => {
    const text = form.translated_text || form.raw_transcript;
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Text copied");
    } catch (error) {
      try {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        toast.success("Text copied");
      } catch (fallbackError) {
        toast.error("Copy was blocked by the browser. Please select and copy manually.");
      }
    }
  };

  const remove = async () => {
    try {
      await api.deleteSession(id);
      toast.success("Session deleted");
      navigate("/history");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Could not delete session");
    }
  };

  if (status !== "completed") {
    return (
      <section className="page-band" data-testid="result-processing-page">
        <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="solid-panel p-8 text-center" data-testid="result-processing-panel">
            <StatusStepper state={status} />
            <h1 className="mt-8 font-heading text-4xl font-bold" data-testid="result-processing-title">Preparing medical text</h1>
            <p className="mt-3 text-[#636965]" data-testid="result-processing-status">Current status: {status}</p>
            {status === "failed" && <Link to="/record" className="earth-button mt-6 inline-flex" data-testid="result-failed-retry-link">Try again</Link>}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="page-band" data-testid="result-page">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end" data-testid="result-header">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-[#D4A373]" data-testid="result-kicker">Completed note</p>
            <h1 className="mt-3 font-heading text-4xl font-bold tracking-normal" data-testid="result-title">Transcript and prescription</h1>
          </div>
          <div className="flex flex-wrap gap-2" data-testid="result-actions">
            <Button onClick={copy} className="earth-button secondary" data-testid="result-copy-button"><Clipboard className="h-4 w-4" /> Copy</Button>
            <Button onClick={download} className="earth-button secondary" data-testid="result-download-button"><Download className="h-4 w-4" /> Download</Button>
            <Button onClick={save} className="earth-button" data-testid="result-save-button"><Save className="h-4 w-4" /> Save</Button>
            <Button onClick={remove} className="earth-button danger" data-testid="result-delete-button"><Trash2 className="h-4 w-4" /> Delete</Button>
          </div>
        </div>
        {result?.warnings?.length > 0 && (
          <div className="warning-band" data-testid="result-warning-banner">{result.warnings.join(" ")}</div>
        )}
        <div className="result-grid mt-6">
          <div className="solid-panel p-5" data-testid="raw-transcript-panel">
            <h2 className="section-title" data-testid="raw-transcript-title">Raw transcript</h2>
            <Textarea value={form.raw_transcript} onChange={(e) => setForm({ ...form, raw_transcript: e.target.value })} className="earth-textarea mt-4" data-testid="raw-transcript-textarea" />
          </div>
          <div className="solid-panel p-5" data-testid="translated-text-panel">
            <h2 className="section-title" data-testid="translated-text-title">Translation</h2>
            <Textarea value={form.translated_text} onChange={(e) => setForm({ ...form, translated_text: e.target.value })} className="earth-textarea mt-4" data-testid="translated-text-textarea" />
          </div>
          <div className="solid-panel p-5 lg:col-span-2" data-testid="prescription-panel">
            <h2 className="section-title" data-testid="prescription-title"><Check className="h-5 w-5 text-[#3D7A5D]" /> Structured prescription</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label data-testid="prescription-symptoms-label"><span className="field-label">Symptoms</span><Textarea value={arrayToText(form.structured_prescription.symptoms)} onChange={(e) => setPrescriptionField("symptoms", e.target.value, true)} className="earth-textarea small" data-testid="prescription-symptoms-textarea" /></label>
              <label data-testid="prescription-medications-label"><span className="field-label">Medications</span><Textarea value={arrayToText(form.structured_prescription.medications)} onChange={(e) => setPrescriptionField("medications", e.target.value, true)} className="earth-textarea small" data-testid="prescription-medications-textarea" /></label>
              <label data-testid="prescription-diagnosis-label"><span className="field-label">Diagnosis</span><Textarea value={form.structured_prescription.diagnosis} onChange={(e) => setPrescriptionField("diagnosis", e.target.value)} className="earth-textarea small" data-testid="prescription-diagnosis-textarea" /></label>
              <label data-testid="prescription-advice-label"><span className="field-label">Advice</span><Textarea value={arrayToText(form.structured_prescription.advice)} onChange={(e) => setPrescriptionField("advice", e.target.value, true)} className="earth-textarea small" data-testid="prescription-advice-textarea" /></label>
              <label className="md:col-span-2" data-testid="prescription-followup-label"><span className="field-label">Follow-up</span><Textarea value={form.structured_prescription.follow_up} onChange={(e) => setPrescriptionField("follow_up", e.target.value)} className="earth-textarea small" data-testid="prescription-followup-textarea" /></label>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
