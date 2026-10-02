import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return (
    <main className="min-h-screen bg-black p-8">
      <div className="max-w-6xl mx-auto">

        <div className="flex items-center justify-between mb-10 border-b border-zinc-800 pb-6">
          <h1 className="text-3xl font-bold text-white tracking-tight">Thouth</h1>
          <span className="text-zinc-500 text-sm">{user.email}</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-zinc-800">
          {[
            { name: "Knowledge Weaver", desc: "Your semantic concept graph." },
            { name: "Cognitive Mirror", desc: "Adaptive mastery tracking." },
            { name: "Study Autopilot", desc: "Deadline and task intelligence." },
          ].map((module) => (
            <div key={module.name} className="bg-black p-6">
              <h2 className="text-white font-semibold mb-2 text-sm uppercase tracking-widest">
                {module.name}
              </h2>
              <p className="text-zinc-600 text-sm">{module.desc}</p>
              <div className="mt-6">
                <span className="text-xs text-zinc-700 border border-zinc-800 px-2 py-1">
                  Sprint in progress
                </span>
              </div>
            </div>
          ))}
        </div>

      </div>
    </main>
  );
}
