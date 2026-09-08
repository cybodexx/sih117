"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { BrandEmblem } from "@/components/BrandEmblem";
import { getStoredToken } from "@/lib/api-client";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      router.replace("/chat/new");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center space-y-3">
        <div className="mx-auto flex w-fit justify-center">
          <BrandEmblem size="lg" />
        </div>
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
          Loading AEGIS-WB…
        </p>
      </div>
    </main>
  );
}