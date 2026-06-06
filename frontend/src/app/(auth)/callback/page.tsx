"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { Skeleton } from "@/components/ui/skeleton";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const userJson = searchParams.get("user");

    if (accessToken && userJson) {
      try {
        const user = JSON.parse(decodeURIComponent(userJson));
        login(accessToken, user);
        router.replace("/videos");
      } catch {
        router.replace("/login");
      }
    } else {
      router.replace("/login");
    }
  }, [searchParams, login, router]);

  return (
    <div className="space-y-4 text-center">
      <Skeleton className="mx-auto h-8 w-48" />
      <p className="text-sm text-muted-foreground">Signing you in...</p>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Suspense
        fallback={
          <div className="space-y-4 text-center">
            <Skeleton className="mx-auto h-8 w-48" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        }
      >
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
