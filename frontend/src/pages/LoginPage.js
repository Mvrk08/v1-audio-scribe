import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LockKeyhole, Mail } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("doctor@clinic.test");
  const [password, setPassword] = useState("demo1234");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await api.login(email, password);
      setToken(response.data.token);
      toast.success("Doctor session opened");
      navigate("/record");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="login-shell" data-testid="login-page">
      <div className="login-panel animate-soft-rise" data-testid="login-panel">
        <p className="text-sm uppercase tracking-[0.2em] text-[#D4A373]" data-testid="login-kicker">Doctor workspace</p>
        <h1 className="mt-4 font-heading text-4xl font-bold tracking-normal text-[#2C302E]" data-testid="login-title">Welcome back</h1>
        <p className="mt-3 text-sm text-[#636965]" data-testid="login-demo-hint">Demo account is pre-filled for the MVP.</p>
        <form className="mt-8 space-y-5" onSubmit={submit} data-testid="login-form">
          <label className="block" data-testid="login-email-label">
            <span className="field-label">Email</span>
            <span className="input-icon-wrap">
              <Mail className="h-4 w-4" aria-hidden="true" />
              <Input value={email} onChange={(e) => setEmail(e.target.value)} className="earth-input pl-10" data-testid="login-email-input" />
            </span>
          </label>
          <label className="block" data-testid="login-password-label">
            <span className="field-label">Password</span>
            <span className="input-icon-wrap">
              <LockKeyhole className="h-4 w-4" aria-hidden="true" />
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="earth-input pl-10" data-testid="login-password-input" />
            </span>
          </label>
          <Button type="submit" disabled={loading} className="earth-button w-full" data-testid="login-submit-button">
            {loading ? "Opening..." : "Open recorder"}
          </Button>
        </form>
      </div>
    </section>
  );
}
