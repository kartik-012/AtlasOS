import { Sidebar } from "@/components/layout/sidebar";
import { Toaster } from "@/components/ui/sonner";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-full relative bg-[#09090b]">
      <div className="hidden h-full md:flex md:w-72 md:col-span-3 lg:col-span-2 md:flex-col md:fixed md:inset-y-0 z-[80]">
        <Sidebar />
      </div>
      <main className="md:pl-72 h-full">
        {/* Top glow effect */}
        <div className="absolute top-0 left-0 right-0 h-[500px] bg-primary/5 rounded-full blur-[150px] pointer-events-none -z-10" />
        <div className="p-8">
          {children}
        </div>
      </main>
      <Toaster theme="dark" />
    </div>
  );
}
