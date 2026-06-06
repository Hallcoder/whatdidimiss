"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getGoogleLoginUrl } from "@/lib/api/auth";

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false);

  async function handleLogin() {
    setIsLoading(true);
    try {
      const { auth_url } = await getGoogleLoginUrl();
      window.location.href = auth_url;
    } catch {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">whatdidimiss</CardTitle>
          <CardDescription>
            AI-powered coaching for your YouTube content. Get data-driven insights on what works and
            what to improve.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            className="w-full"
            size="lg"
            onClick={handleLogin}
            disabled={isLoading}
          >
            {isLoading ? "Redirecting..." : "Sign in with Google"}
          </Button>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Signing in grants access to your YouTube analytics for content analysis.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
