"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { Film, LayoutDashboard, Link2, LogOut, Tv } from "lucide-react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/components/providers/auth-provider";
import { getGoogleLoginUrl } from "@/lib/api/auth";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/videos", label: "Videos", icon: Film },
  { href: "/videos/browse", label: "Browse Channel", icon: Tv },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isConnecting, setIsConnecting] = useState(false);

  async function handleLogout() {
    await logout();
    toast.success("Signed out");
    router.push("/login");
  }

  async function handleConnectChannel() {
    setIsConnecting(true);
    try {
      const { auth_url } = await getGoogleLoginUrl();
      window.location.href = auth_url;
    } catch {
      toast.error("Failed to start channel connection");
      setIsConnecting(false);
    }
  }

  const hasChannel = !!user?.channel;

  return (
    <aside className="flex h-full w-60 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center px-4">
        <Link href="/videos" className="flex items-center gap-2">
          <LayoutDashboard className="h-5 w-5 text-primary" />
          <span className="text-lg font-semibold">whatdidimiss</span>
        </Link>
      </div>

      <Separator />

      <nav className="flex-1 space-y-1 px-2 py-3">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <Separator />

      {/* Channel status */}
      <div className="px-3 py-3">
        {hasChannel ? (
          <div className="rounded-md bg-accent/50 px-3 py-2">
            <p className="truncate text-xs font-medium">{user.channel!.channel_title}</p>
            {user.channel!.subscriber_count != null && (
              <p className="text-[10px] text-muted-foreground">
                {user.channel!.subscriber_count.toLocaleString()} subscribers
              </p>
            )}
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={handleConnectChannel}
            disabled={isConnecting}
          >
            <Link2 className="mr-2 h-3.5 w-3.5" />
            {isConnecting ? "Connecting..." : "Connect Channel"}
          </Button>
        )}
      </div>

      <Separator />

      <div className="flex items-center gap-3 px-4 py-3">
        <Avatar className="h-8 w-8">
          <AvatarImage src={user?.avatar_url ?? undefined} />
          <AvatarFallback>
            {user?.display_name?.charAt(0).toUpperCase() ?? "U"}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 truncate">
          <p className="truncate text-sm font-medium">{user?.display_name ?? "User"}</p>
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={handleLogout} title="Sign out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </aside>
  );
}
