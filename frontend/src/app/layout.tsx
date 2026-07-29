import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/lib/auth-context";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AtlasOS - Developer Console",
  description: "Next-generation developer console for AtlasOS",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen bg-background antialiased selection:bg-primary/30 mesh-gradient`}>
        <AuthProvider>
          {children}
          <Toaster theme="light" position="top-right" />
        </AuthProvider>
      </body>
    </html>
  );
}
