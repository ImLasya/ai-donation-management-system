import { createFileRoute, Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { ArrowRight, Eye, EyeOff, HeartHandshake } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useApp } from "@/context/AppContext";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Sign in — Donate" },
      { name: "description", content: "Sign in to your Donate donor, NGO, or admin portal." },
    ],
  }),
  component: Login,
});

function Login() {
  const { user, authenticate } = useApp();
  const navigate = useNavigate();
  const { redirect } = Route.useSearch();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; submit?: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [activeRole, setActiveRole] = useState<"donor" | "ngo" | "admin" | null>(null);

  const selectRole = (role: "donor" | "ngo" | "admin") => {
    setActiveRole(role);
    setErrors({});
    if (role === "donor") {
      setEmail("aarav@example.com");
      setPassword("Donor@2026");
    } else if (role === "ngo") {
      setEmail("priya@hopefoundation.org");
      setPassword("Ngo@2026");
    } else if (role === "admin") {
      setEmail("admin@donateai.org");
      setPassword("Admin@2026");
    }
  };

  // Load remembered email
  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedEmail = window.localStorage.getItem("donateai-remember-email");
    if (savedEmail) {
      setEmail(savedEmail);
      setRememberMe(true);
    }
  }, []);

  // Handle auto-redirection on login state change
  useEffect(() => {
    if (!user) return;

    let destination = "/";
    if (redirect && redirect.startsWith("/")) {
      // Ensure the redirect matches the user's role path prefix
      if (redirect.startsWith("/donor/") && user.role === "donor") {
        destination = redirect;
      } else if (redirect.startsWith("/ngo/") && user.role === "ngo") {
        destination = redirect;
      } else if (redirect.startsWith("/admin/") && user.role === "admin") {
        destination = redirect;
      } else {
        // Redirection mismatch or invalid path, fallback to standard dashboard
        destination =
          user.role === "donor"
            ? "/donor/dashboard"
            : user.role === "ngo"
              ? "/ngo/dashboard"
              : "/admin/dashboard";
      }
    } else {
      destination =
        user.role === "donor"
          ? "/donor/dashboard"
          : user.role === "ngo"
            ? "/ngo/dashboard"
            : "/admin/dashboard";
    }

    navigate({ to: destination });
  }, [navigate, redirect, user]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: { email?: string; password?: string } = {};

    if (!email.trim()) {
      nextErrors.email = "Email is required.";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      nextErrors.email = "Please enter a valid email address.";
    }

    if (!password.trim()) {
      nextErrors.password = "Password is required.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    const result = await authenticate(email, password);
    if (result.success) {
      if (rememberMe) {
        window.localStorage.setItem("donateai-remember-email", email);
      } else {
        window.localStorage.removeItem("donateai-remember-email");
      }
      return;
    }

    setErrors({ submit: result.error || "We couldn't sign you in with those credentials." });
    setSubmitting(false);
  };

  const helperText = useMemo(() => {
    if (redirect?.startsWith("/donor/")) return "Sign in to continue to your donation workspace.";
    if (redirect?.startsWith("/ngo/")) return "Sign in to continue to your NGO workspace.";
    if (redirect?.startsWith("/admin/")) return "Sign in to continue to your Admin workspace.";
    return "Access your secure Donate workspace.";
  }, [redirect]);

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
      {/* Brand Side Panel */}
      <div className="hidden flex-col justify-between bg-gradient-to-br from-primary to-primary-dark p-12 text-primary-foreground lg:flex">
        <Link to="/" className="flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary-foreground/15">
            <HeartHandshake className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold">Donate</span>
        </Link>
        <div>
          <h2 className="text-3xl font-bold">Secure sign-in for trusted donation operations.</h2>
          <p className="mt-4 max-w-md text-primary-foreground/80">
            Access your donor, NGO, or admin workspace with the same modern experience used by
            verified partners.
          </p>
        </div>
        <p className="text-sm text-primary-foreground/60">
          Built for real-world coordination and transparent impact.
        </p>
      </div>

      {/* Form Side Panel */}
      <div className="flex items-center justify-center bg-background p-6 sm:p-8">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <Link to="/" className="inline-flex items-center gap-2">
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
                <HeartHandshake className="h-5 w-5" />
              </div>
              <span className="text-lg font-bold text-foreground">Donate</span>
            </Link>
          </div>

          <div className="rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-8">
            <h1 className="text-2xl font-bold text-foreground">Welcome back</h1>
            <p className="mt-2 text-sm text-muted-foreground">{helperText}</p>

            {/* Role Selection Row */}
            <div className="mt-5 flex rounded-xl bg-muted p-1 text-sm font-semibold border border-border">
              <button
                type="button"
                className={cn(
                  "flex-1 rounded-lg py-2 text-center transition-all cursor-pointer",
                  activeRole === "donor"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
                onClick={() => selectRole("donor")}
              >
                Donor
              </button>
              <button
                type="button"
                className={cn(
                  "flex-1 rounded-lg py-2 text-center transition-all cursor-pointer",
                  activeRole === "ngo"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
                onClick={() => selectRole("ngo")}
              >
                NGO
              </button>
              <button
                type="button"
                className={cn(
                  "flex-1 rounded-lg py-2 text-center transition-all cursor-pointer",
                  activeRole === "admin"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
                onClick={() => selectRole("admin")}
              >
                Admin
              </button>
            </div>

            <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    if (errors.email) setErrors((current) => ({ ...current, email: undefined }));
                  }}
                  className="mt-1"
                />
                {errors.email && <p className="mt-1 text-sm text-destructive">{errors.email}</p>}
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    to="/login"
                    onClick={(e) => {
                      e.preventDefault();
                      alert("Password reset functionality is not configured.");
                    }}
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative mt-1">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      if (errors.password)
                        setErrors((current) => ({ ...current, password: undefined }));
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute inset-y-0 right-3 flex items-center text-muted-foreground"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-1 text-sm text-destructive">{errors.password}</p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  id="remember"
                  checked={rememberMe}
                  onCheckedChange={(checked) => setRememberMe(Boolean(checked))}
                />
                <Label
                  htmlFor="remember"
                  className="text-sm font-normal text-muted-foreground cursor-pointer"
                >
                  Remember me
                </Label>
              </div>

              {errors.submit && (
                <p className="text-sm text-destructive font-medium">{errors.submit}</p>
              )}

              <Button type="submit" className="w-full gap-2 mt-2" disabled={submitting}>
                {submitting ? "Signing in..." : "Sign In"}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </form>

            <div className="mt-8 border-t border-border pt-6">
              <p className="text-center text-sm text-muted-foreground">Don’t have an account?</p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <Link
                  to="/register/donor"
                  className="flex items-center justify-center rounded-lg border border-border bg-background px-3 py-2.5 text-center text-xs font-semibold text-foreground hover:bg-accent transition-colors"
                >
                  Register as Donor
                </Link>
                <Link
                  to="/register/ngo"
                  className="flex items-center justify-center rounded-lg border border-border bg-background px-3 py-2.5 text-center text-xs font-semibold text-foreground hover:bg-accent transition-colors"
                >
                  Register your NGO
                </Link>
              </div>
            </div>
          </div>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            <Link to="/" className="text-primary hover:underline">
              Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
