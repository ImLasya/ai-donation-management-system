import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowRight, Eye, EyeOff, HeartHandshake } from "lucide-react";
import { useState } from "react";
import { useApp } from "@/context/AppContext";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/register/ngo")({
  head: () => ({
    meta: [
      { title: "Register your NGO — Donate" },
      {
        name: "description",
        content: "Register your NGO with Donate to coordinate and receive matched donations.",
      },
    ],
  }),
  component: RegisterNGO,
});

const CATEGORY_OPTIONS = [
  "Clothing",
  "Food",
  "Books",
  "Education",
  "Electronics",
  "Furniture",
  "Kitchen",
  "Household",
  "Hygiene",
  "Toys",
  "Medical",
];

function RegisterNGO() {
  const { register } = useApp();
  const navigate = useNavigate();

  const [orgName, setOrgName] = useState("");
  const [regNum, setRegNum] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [mission, setMission] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [terms, setTerms] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleCategoryChange = (category: string, checked: boolean) => {
    if (checked) {
      setSelectedCategories((prev) => [...prev, category]);
    } else {
      setSelectedCategories((prev) => prev.filter((c) => c !== category));
    }
    if (errors.focusAreas) {
      setErrors((current) => ({ ...current, focusAreas: "" }));
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};

    if (!orgName.trim()) nextErrors.orgName = "Organisation name is required.";
    if (!regNum.trim()) nextErrors.regNum = "Registration number is required.";
    if (!contactPerson.trim()) nextErrors.contactPerson = "Contact person is required.";

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

    if (!address.trim()) nextErrors.address = "Address is required.";
    if (!city.trim()) nextErrors.city = "City is required.";
    if (!state.trim()) nextErrors.state = "State is required.";

    if (selectedCategories.length === 0) {
      nextErrors.focusAreas = "Please select at least one focus area.";
    }

    if (!mission.trim()) nextErrors.mission = "Organisation mission statement is required.";

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
      name: contactPerson,
      email,
      role: "ngo",
      password,
      org: orgName,
      phone,
      city,
      state,
      registrationNumber: regNum,
      contactPerson,
      address,
      focusAreas: selectedCategories.join(", "),
      mission,
    });

    if (result.success) {
      navigate({ to: "/login" });
      return;
    }

    setErrors({ submit: result.error || "An error occurred during registration." });
    setSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
              <HeartHandshake className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold text-foreground">Donate</span>
          </Link>
          <Link to="/login" className="text-sm font-medium text-primary hover:underline">
            Sign in
          </Link>
        </div>

        <div className="rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-10">
          <div className="border-b border-border pb-6">
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
              Register your NGO
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Connect your organisation to Donate to receive verified items that match your
              demands.
            </p>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {/* General Info */}
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-foreground border-l-4 border-primary pl-2">
                Organisation Information
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="orgName">Organisation Name</Label>
                  <Input
                    id="orgName"
                    placeholder="Hope Foundation"
                    value={orgName}
                    onChange={(event) => {
                      setOrgName(event.target.value);
                      if (errors.orgName) setErrors((current) => ({ ...current, orgName: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.orgName && (
                    <p className="mt-1 text-sm text-destructive">{errors.orgName}</p>
                  )}
                </div>
                <div>
                  <Label htmlFor="regNum">Registration Number / ID</Label>
                  <Input
                    id="regNum"
                    placeholder="NGO-12345-AA"
                    value={regNum}
                    onChange={(event) => {
                      setRegNum(event.target.value);
                      if (errors.regNum) setErrors((current) => ({ ...current, regNum: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.regNum && (
                    <p className="mt-1 text-sm text-destructive">{errors.regNum}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Contact Person */}
            <div className="space-y-4 pt-2">
              <h2 className="text-lg font-semibold text-foreground border-l-4 border-primary pl-2">
                Contact Details
              </h2>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="sm:col-span-1">
                  <Label htmlFor="contactPerson">Contact Person</Label>
                  <Input
                    id="contactPerson"
                    placeholder="Priya Nair"
                    value={contactPerson}
                    onChange={(event) => {
                      setContactPerson(event.target.value);
                      if (errors.contactPerson)
                        setErrors((current) => ({ ...current, contactPerson: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.contactPerson && (
                    <p className="mt-1 text-sm text-destructive">{errors.contactPerson}</p>
                  )}
                </div>
                <div className="sm:col-span-1">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="contact@hopefoundation.org"
                    value={email}
                    onChange={(event) => {
                      setEmail(event.target.value);
                      if (errors.email) setErrors((current) => ({ ...current, email: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.email && <p className="mt-1 text-sm text-destructive">{errors.email}</p>}
                </div>
                <div className="sm:col-span-1">
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="+91 80 4000 1234"
                    value={phone}
                    onChange={(event) => {
                      setPhone(event.target.value);
                      if (errors.phone) setErrors((current) => ({ ...current, phone: "" }));
                    }}
                    className="mt-1"
                  />
                  {errors.phone && <p className="mt-1 text-sm text-destructive">{errors.phone}</p>}
                </div>
              </div>
            </div>

            {/* Address */}
            <div className="space-y-4 pt-2">
              <h2 className="text-lg font-semibold text-foreground border-l-4 border-primary pl-2">
                Location
              </h2>
              <div>
                <Label htmlFor="address">Full Address</Label>
                <Input
                  id="address"
                  placeholder="12 Residency Road"
                  value={address}
                  onChange={(event) => {
                    setAddress(event.target.value);
                    if (errors.address) setErrors((current) => ({ ...current, address: "" }));
                  }}
                  className="mt-1"
                />
                {errors.address && (
                  <p className="mt-1 text-sm text-destructive">{errors.address}</p>
                )}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
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
            </div>

            {/* Focus Areas & Mission */}
            <div className="space-y-4 pt-2">
              <h2 className="text-lg font-semibold text-foreground border-l-4 border-primary pl-2">
                Focus Areas & Mission
              </h2>
              <div>
                <Label>Focus Areas (select all that apply)</Label>
                <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-xl border border-border bg-muted/30 p-4">
                  {CATEGORY_OPTIONS.map((category) => (
                    <div key={category} className="flex items-center gap-2">
                      <Checkbox
                        id={`cat-${category}`}
                        checked={selectedCategories.includes(category)}
                        onCheckedChange={(checked) =>
                          handleCategoryChange(category, Boolean(checked))
                        }
                      />
                      <Label
                        htmlFor={`cat-${category}`}
                        className="text-xs font-normal text-foreground cursor-pointer"
                      >
                        {category}
                      </Label>
                    </div>
                  ))}
                </div>
                {errors.focusAreas && (
                  <p className="mt-1 text-sm text-destructive">{errors.focusAreas}</p>
                )}
              </div>

              <div>
                <Label htmlFor="mission">Mission Statement</Label>
                <Textarea
                  id="mission"
                  placeholder="Empowering children through education, providing resources for families, and supporting community development..."
                  value={mission}
                  onChange={(event) => {
                    setMission(event.target.value);
                    if (errors.mission) setErrors((current) => ({ ...current, mission: "" }));
                  }}
                  className="mt-1 min-h-[80px]"
                />
                {errors.mission && (
                  <p className="mt-1 text-sm text-destructive">{errors.mission}</p>
                )}
              </div>
            </div>

            {/* Password */}
            <div className="space-y-4 pt-2">
              <h2 className="text-lg font-semibold text-foreground border-l-4 border-primary pl-2">
                Account Credentials
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
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
              </div>
            </div>

            {/* Terms and Submission */}
            <div className="space-y-4 pt-4 border-t border-border">
              <div className="space-y-1">
                <div className="flex items-start gap-2">
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
                    We certify that this NGO is a registered entity, and we agree to the{" "}
                    <Link
                      to="/register/ngo"
                      onClick={(e) => {
                        e.preventDefault();
                        alert("Terms of Service are located in the documentation.");
                      }}
                      className="text-primary hover:underline"
                    >
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link
                      to="/register/ngo"
                      onClick={(e) => {
                        e.preventDefault();
                        alert("Privacy Policy is located in the documentation.");
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

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pt-2">
                <p className="text-sm text-muted-foreground">
                  Already have an account?{" "}
                  <Link to="/login" className="font-semibold text-primary hover:underline">
                    Sign in
                  </Link>
                </p>
                <Button type="submit" size="lg" className="gap-2 sm:w-auto" disabled={submitting}>
                  {submitting ? "Registering NGO..." : "Register NGO"}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
