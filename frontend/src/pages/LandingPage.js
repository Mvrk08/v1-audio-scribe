import { Link } from "react-router-dom";
import { ArrowRight, Clock3, FileText, ShieldCheck } from "lucide-react";

const heroImage = "https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHwxfHxkb2N0b3IlMjBwYXRpZW50JTIwY29uc3VsdGF0aW9ufGVufDB8fHx8MTc3NzY5OTEyNXww&ixlib=rb-4.1.0&q=85";

export default function LandingPage() {
  return (
    <div data-testid="landing-page">
      <section className="relative min-h-[78vh] overflow-hidden" data-testid="landing-hero-section">
        <img src={heroImage} alt="Doctor consulting with a patient" className="absolute inset-0 h-full w-full object-cover object-center" data-testid="landing-hero-image" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#243127]/85 via-[#243127]/55 to-transparent" />
        <div className="relative mx-auto flex min-h-[78vh] max-w-7xl items-center px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-2xl text-white animate-soft-rise">
            <p className="mb-5 text-sm uppercase tracking-[0.2em] text-[#F2D7B8]" data-testid="landing-hero-kicker">Medical voice notes in under two minutes</p>
            <h1 className="font-heading text-4xl font-bold leading-tight tracking-normal sm:text-5xl lg:text-6xl" data-testid="landing-hero-title">
              Turn short consultations into editable prescriptions.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-white/88" data-testid="landing-hero-subtitle">
              Record or upload a doctor-patient interaction, review the transcript, translate it, and export structured medical notes.
            </p>
            <Link to="/login" className="earth-button hero mt-8 inline-flex" data-testid="landing-start-button">
              Start session <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>
      <section className="mx-auto grid max-w-7xl gap-4 px-4 py-8 sm:grid-cols-3 sm:px-6 lg:px-8" data-testid="landing-capabilities-section">
        {[
          [Clock3, "120 sec", "Strict short-visit recording window"],
          [ShieldCheck, "Temporary audio", "Audio is removed after processing"],
          [FileText, "Text product", "Transcript, translation, prescription"],
        ].map(([Icon, value, label]) => (
          <div className="metric-tile" key={value} data-testid={`landing-metric-${value.toString().replace(/\s+/g, '-').toLowerCase()}`}>
            <Icon className="h-5 w-5 text-[#4A5D4E]" aria-hidden="true" />
            <div>
              <p className="font-heading text-xl font-bold" data-testid={`landing-metric-value-${value.toString().replace(/\s+/g, '-').toLowerCase()}`}>{value}</p>
              <p className="text-sm text-[#636965]" data-testid={`landing-metric-label-${value.toString().replace(/\s+/g, '-').toLowerCase()}`}>{label}</p>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
