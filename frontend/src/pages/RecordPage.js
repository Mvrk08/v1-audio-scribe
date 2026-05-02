import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileAudio, Mic, Pause, UploadCloud, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { StatusStepper } from "@/components/StatusStepper";

const MAX_SECONDS = 120;
const MAX_BYTES = 25 * 1024 * 1024;
const extensions = ["webm", "wav", "mp3", "m4a", "aac", "flac", "ogg", "mp4"];

const mimeType = () => {
  if (window.MediaRecorder?.isTypeSupported("audio/webm;codecs=opus")) return "audio/webm;codecs=opus";
  if (window.MediaRecorder?.isTypeSupported("audio/mp4")) return "audio/mp4";
  return "";
};

export default function RecordPage() {
  const [source, setSource] = useState("auto");
  const [target, setTarget] = useState("en");
  const [state, setState] = useState("idle");
  const [seconds, setSeconds] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const stream = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (state !== "recording") return undefined;
    const timer = setInterval(() => {
      setSeconds((current) => {
        if (current + 1 >= MAX_SECONDS) stopRecording();
        return Math.min(current + 1, MAX_SECONDS);
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [state]);

  const validateFile = (file) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!extensions.includes(ext)) {
      toast.error("Unsupported audio format");
      return false;
    }
    if (file.size > MAX_BYTES) {
      toast.error("Audio must be smaller than 25MB");
      return false;
    }
    return true;
  };

  const startRecording = async () => {
    try {
      chunks.current = [];
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = audioStream;
      const recorder = new MediaRecorder(audioStream, mimeType() ? { mimeType: mimeType() } : undefined);
      recorder.ondataavailable = (event) => event.data.size && chunks.current.push(event.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: recorder.mimeType || "audio/webm" });
        setRecordedBlob(blob);
        setSelectedFile(new File([blob], "consultation-recording.webm", { type: blob.type || "audio/webm" }));
        setState("idle");
        toast.success("Recording ready for processing");
      };
      mediaRecorder.current = recorder;
      setSeconds(0);
      setSelectedFile(null);
      setRecordedBlob(null);
      recorder.start();
      setState("recording");
    } catch (error) {
      if (error.name === "NotAllowedError") toast.error("Microphone permission was denied");
      else toast.error("Could not start microphone recording");
      setState("failed");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
      setState("stopping");
      mediaRecorder.current.stop();
    }
    stream.current?.getTracks().forEach((track) => track.stop());
  };

  const onFile = (file) => {
    if (!file || !validateFile(file)) return;
    setSelectedFile(file);
    setRecordedBlob(null);
    setSeconds(0);
    toast.success("Audio file selected");
  };

  const submitAudio = async () => {
    if (!selectedFile) {
      toast.error("Record or upload audio first");
      return;
    }
    setState("uploading");
    try {
      const created = await api.createSession(source, target);
      const sessionId = created.data.id;
      await api.uploadAudio(sessionId, selectedFile, recordedBlob ? seconds : 0);
      setState("processing");
      await api.processSession(sessionId);
      navigate(`/result/${sessionId}`);
    } catch (error) {
      setState("failed");
      toast.error(error.response?.data?.detail || "Processing could not start");
    }
  };

  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  const secs = String(seconds % 60).padStart(2, "0");
  const busy = ["recording", "stopping", "uploading", "processing"].includes(state);

  return (
    <section className="page-band" data-testid="record-page">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 max-w-3xl animate-soft-rise">
          <p className="text-sm uppercase tracking-[0.2em] text-[#D4A373]" data-testid="record-kicker">New consultation</p>
          <h1 className="mt-3 font-heading text-4xl font-bold tracking-normal sm:text-5xl" data-testid="record-title">Capture the visit, keep the text.</h1>
        </div>
        <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="solid-panel p-6 sm:p-8" data-testid="record-control-panel">
            <StatusStepper state={state === "stopping" ? "recording" : state} />
            <div className="timer-orb" data-testid="record-timer-display">
              <span>{minutes}:{secs}</span>
              <small>max 02:00</small>
            </div>
            <div className="mt-8 flex flex-wrap gap-3" data-testid="record-button-row">
              {state === "recording" ? (
                <Button onClick={stopRecording} className="earth-button danger" data-testid="record-stop-button">
                  <Pause className="h-4 w-4" aria-hidden="true" /> Stop
                </Button>
              ) : (
                <Button onClick={startRecording} disabled={busy} className="earth-button" data-testid="record-start-button">
                  <Mic className="h-4 w-4" aria-hidden="true" /> Record audio
                </Button>
              )}
              <Button onClick={submitAudio} disabled={!selectedFile || busy} className="earth-button accent" data-testid="record-process-button">
                <UploadCloud className="h-4 w-4" aria-hidden="true" /> Upload & process
              </Button>
              {selectedFile && (
                <Button onClick={() => setSelectedFile(null)} disabled={busy} className="earth-button secondary" data-testid="record-clear-file-button">
                  <X className="h-4 w-4" aria-hidden="true" /> Clear
                </Button>
              )}
            </div>
          </div>
          <div className="space-y-6">
            <div className="solid-panel p-6" data-testid="language-panel">
              <h2 className="font-heading text-2xl font-semibold" data-testid="language-title">Languages</h2>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <label data-testid="source-language-label">
                  <span className="field-label">Input</span>
                  <select value={source} onChange={(e) => setSource(e.target.value)} className="earth-select" data-testid="source-language-select">
                    <option value="auto">Auto detect</option>
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="pa">Punjabi</option>
                  </select>
                </label>
                <label data-testid="target-language-label">
                  <span className="field-label">Output</span>
                  <select value={target} onChange={(e) => setTarget(e.target.value)} className="earth-select" data-testid="target-language-select">
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="pa">Punjabi</option>
                  </select>
                </label>
              </div>
            </div>
            <label
              className="drop-zone"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                onFile(event.dataTransfer.files?.[0]);
              }}
              data-testid="audio-drop-zone"
            >
              <FileAudio className="h-8 w-8 text-[#4A5D4E]" aria-hidden="true" />
              <span data-testid="selected-audio-name">{selectedFile ? selectedFile.name : "Drop audio here or browse"}</span>
              <small data-testid="audio-upload-rules">WebM, WAV, MP3, M4A, AAC, FLAC, OGG • 25MB max</small>
              <input type="file" accept="audio/*,.webm,.wav,.mp3,.m4a,.aac,.flac,.ogg" onChange={(e) => onFile(e.target.files?.[0])} data-testid="audio-file-input" />
            </label>
          </div>
        </div>
      </div>
    </section>
  );
}
