import React from "react";
import { Input, Button } from "@heroui/react";
import { Icon } from "@iconify/react";

const Login: React.FC = () => {
  const [email, setEmail] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [sent, setSent] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setIsLoading(false);
    setSent(true);
    console.log("Magic link requested for:", email);
  };

  return (
    <div
      className="flex min-h-screen"
      style={{
        backgroundColor: "var(--background)",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      {/* Left panel - branding */}
      <div
        className="hidden lg:flex flex-col justify-between w-80 p-8 shrink-0"
        style={{
          backgroundColor: "var(--primary)",
          color: "#fff",
        }}
      >
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center rounded-lg bg-white/20 p-1.5">
            <Icon icon="lucide:zap" width={20} height={20} />
          </div>
          <span className="font-semibold text-lg">Devengo</span>
        </div>
        <div>
          <p className="text-white/70 text-sm leading-relaxed">
            Accrual management platform for modern finance teams.
          </p>
        </div>
      </div>

      {/* Right panel - form */}
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-2 mb-8">
            <div
              className="flex items-center justify-center rounded-lg p-1.5"
              style={{ backgroundColor: "var(--primary)", color: "#fff" }}
            >
              <Icon icon="lucide:zap" width={20} height={20} />
            </div>
            <span
              className="font-semibold text-lg"
              style={{ color: "var(--foreground)" }}
            >
              Devengo
            </span>
          </div>

          <h1
            className="text-2xl font-bold mb-1"
            style={{ color: "var(--foreground)" }}
          >
            Sign in
          </h1>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--muted-foreground)" }}
          >
            Enter your email to receive a magic link
          </p>

          {sent ? (
            <div
              className="flex items-start gap-3 p-4 rounded-lg"
              style={{
                backgroundColor: "hsl(207.4 92.7% 95%)",
                border: "1px solid hsl(207.4 92.7% 80%)",
              }}
            >
              <Icon
                icon="lucide:mail-check"
                width={20}
                height={20}
                style={{ color: "var(--primary)", marginTop: 2 }}
              />
              <div>
                <p
                  className="text-sm font-medium"
                  style={{ color: "var(--primary)" }}
                >
                  Check your inbox
                </p>
                <p
                  className="text-xs mt-0.5"
                  style={{ color: "var(--muted-foreground)" }}
                >
                  We sent a magic link to <strong>{email}</strong>
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input
                type="email"
                label="Email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                startContent={
                  <Icon
                    icon="lucide:mail"
                    width={16}
                    height={16}
                    style={{ color: "var(--muted-foreground)" }}
                  />
                }
                variant="bordered"
                isRequired
              />
              <Button
                color="primary"
                type="submit"
                isLoading={isLoading}
                className="font-medium"
                fullWidth
              >
                Send Magic Link
              </Button>
            </form>
          )}

          <p
            className="text-xs mt-6 text-center"
            style={{ color: "var(--muted-foreground)" }}
          >
            By signing in you agree to our terms of service.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
