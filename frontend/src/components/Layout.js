import { Link, NavLink, useNavigate } from "react-router-dom";
import { FileClock, LogOut, Mic2, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { clearToken, getToken } from "@/lib/api";

export const Layout = ({ children }) => {
  const navigate = useNavigate();
  const authed = Boolean(getToken());

  const logout = () => {
    clearToken();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-[#2C302E]" data-testid="app-shell">
      <header className="sticky top-0 z-40 border-b border-white/40 bg-white/75 backdrop-blur-xl" data-testid="main-header">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3" data-testid="brand-home-link">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#4A5D4E] text-white">
              <Stethoscope className="h-5 w-5" aria-hidden="true" />
            </span>
            <span className="font-heading text-lg font-bold tracking-normal" data-testid="brand-name">CareScribe</span>
          </Link>
          <nav className="flex items-center gap-2" data-testid="main-navigation">
            {authed ? (
              <>
                <NavLink to="/record" className="nav-pill" data-testid="nav-record-link">
                  <Mic2 className="h-4 w-4" aria-hidden="true" /> Record
                </NavLink>
                <NavLink to="/history" className="nav-pill" data-testid="nav-history-link">
                  <FileClock className="h-4 w-4" aria-hidden="true" /> History
                </NavLink>
                <Button onClick={logout} className="earth-button secondary" data-testid="logout-button">
                  <LogOut className="h-4 w-4" aria-hidden="true" /> Logout
                </Button>
              </>
            ) : (
              <Link to="/login" className="earth-button inline-flex" data-testid="nav-login-link">Doctor login</Link>
            )}
          </nav>
        </div>
      </header>
      <main data-testid="main-content">{children}</main>
    </div>
  );
};
