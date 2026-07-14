import { redirect } from "next/navigation";

export default function Home() {
  // Simple redirect to the dashboard. The API interceptor/middleware
  // will handle redirecting to /login if unauthenticated.
  redirect("/dashboard");
}
