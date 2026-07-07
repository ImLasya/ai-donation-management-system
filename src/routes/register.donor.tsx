import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowRight, Eye, EyeOff, HeartHandshake } from "lucide-react";
import { useState } from "react";
import { useApp } from "@/context/AppContext";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/register/donor")({
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Register as Donor — Donate" },
      { name: "description", content: "Create a donor account to scan items and support NGOs." },
    ],
  }),
  component: RegisterDonor,
});

function RegisterDonor() {
  const { register } = useApp();
  const navigate = useNavigate();
  const { redirect } = Route.useSearch();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [terms, setTerms] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};

    if (!name.trim()) nextErrors.name = "Full name is required.";

    if (!email.trim()) {
      nextErrors.email = "Email is required.";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      nextErrors.email = "Please enter a valid email address.";
    }

    if (!phone.trim()) {
      nextErrors.phone = "Phone number is required.";
    } else if (!/^\+?[0-9\s\-()]{10,15}$/.test(phone)) {
      nextErrors.phone = "Please enter a valid phone number.";
    }

    if (!city.trim()) nextErrors.city = "City is required.";
    if (!state.trim()) nextErrors.state = "State is required.";

    if (!password) {
      nextErrors.password = "Password is required.";
    } else if (password.length < 6) {
      nextErrors.password = "Password must be at least 6 characters.";
    }

    if (!confirmPassword) {
      nextErrors.confirmPassword = "Confirm password is required.";
    } else if (password !== confirmPassword) {
      nextErrors.confirmPassword = "Passwords do not match.";
    }

    if (!terms) {
      nextErrors.terms = "You must agree to the Terms of Service.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    const result = await register({
      name,
      email,
      role: "donor",
      password,
      phone,
      city,
      state,
    });

    if (result.success) {
      navigate({ to: "/login", search: redirect ? { redirect } : undefined });
      return;
    }

    setErrors({ submit: result.error || "An error occurred during registration." });
    setSubmitting(false);
  };

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
          <h2 className="text-3xl font-bold">Join our community of smart donors.</h2>
          <p className="mt-4 max-w-md text-primary-foreground/80">
            Create an account to scan items with your camera, match them automatically to local
            verified NGOs, and track impact.
          </p>
        </div>
        <p className="text-sm text-primary-foreground/60">
          Help coordinate food, clothing, books, and resources.
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
            <h1 className="text-2xl font-bold text-foreground">Register as Donor</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Start giving back in a smart, transparent way.
            </p>

            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
              <div>
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  placeholder="Aarav Sharma"
                  value={name}
                  onChange={(event) => {
                    setName(event.target.value);
                    if (errors.name) setErrors((current) => ({ ...current, name: "" }));
                  }}
                  className="mt-1"
                />
                {errors.name && <p className="mt-1 text-sm text-destructive">{errors.name}</p>}
              </div>

              <div>
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="aarav@example.com"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    if (errors.email) setErrors((current) => ({ ...current, email: "" }));
                  }}
                  className="mt-1"
                />
                {errors.email && <p className="mt-1 text-sm text-destructive">{errors.email}</p>}
              </div>

              <div>
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="+91 98765 43210"
                  value={phone}
                  onChange={(event) => {
                    setPhone(event.target.value);
                    if (errors.phone) setErrors((current) => ({ ...current, phone: "" }));
                  }}
                  className="mt-1"
                />
                {errors.phone && <p className="mt-1 text-sm text-destructive">{errors.phone}</p>}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="city">City</Label>
                  <Input
                    id="city"
                    placeholder="Bengaluru"
                    value={city}
                    onChange={(event) => {
                      setCity(event.target.value);
                      if (errors.city) setErrors((current) => ({ ...current, city: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.city && <p className="mt-1 text-sm text-destructive">{errors.city}</p>}
                </div>
                <div>
                  <Label htmlFor="state">State</Label>
                  <Input
                    id="state"
                    placeholder="Karnataka"
                    value={state}
                    onChange={(event) => {
                      setState(event.target.value);
                      if (errors.state) setErrors((current) => ({ ...current, state: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.state && <p className="mt-1 text-sm text-destructive">{errors.state}</p>}
                </div>
              </div>

              <div>
                <Label htmlFor="password">Password</Label>
                <div className="relative mt-1">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Create a password"
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      if (errors.password) setErrors((current) => ({ ...current, password: "" }));
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

              <div>
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <div className="relative mt-1">
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm your password"
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                      if (errors.confirmPassword)
                        setErrors((current) => ({ ...current, confirmPassword: "" }));
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((value) => !value)}
                    className="absolute inset-y-0 right-3 flex items-center text-muted-foreground"
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-1 text-sm text-destructive">{errors.confirmPassword}</p>
                )}
              </div>

              <div className="space-y-1">
                <div className="flex items-start gap-2 pt-2">
                  <Checkbox
                    id="terms"
                    checked={terms}
                    onCheckedChange={(checked) => {
                      setTerms(Boolean(checked));
                      if (errors.terms) setErrors((current) => ({ ...current, terms: "" }));
                    }}
                    className="mt-1"
                  />
                  <Label
                    htmlFor="terms"
                    className="text-xs font-normal leading-normal text-muted-foreground cursor-pointer"
                  >
                    I agree to the{" "}
                    <Link
                      to="/register/donor"
                      onClick={(e) => {
                        e.preventDefault();
                        alert("Terms & Conditions can be reviewed in our documentation.");
                      }}
                      className="text-primary hover:underline"
                    >
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link
                      to="/register/donor"
                      onClick={(e) => {
                        e.preventDefault();
                        alert("Privacy Policy can be reviewed in our documentation.");
                      }}
                      className="text-primary hover:underline"
                    >
                      Privacy Policy
                    </Link>
                    .
                  </Label>
                </div>
                {errors.terms && <p className="text-xs text-destructive">{errors.terms}</p>}
              </div>

              {errors.submit && (
                <p className="text-sm text-destructive font-medium">{errors.submit}</p>
              )}

              <Button type="submit" className="w-full gap-2 mt-2" disabled={submitting}>
                {submitting ? "Creating account..." : "Sign Up"}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="font-semibold text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
