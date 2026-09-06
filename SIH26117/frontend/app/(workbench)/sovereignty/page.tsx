import { ProofPanel } from "@/components/sovereignty/ProofPanel";

export default function SovereigntyPage() {
  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Sovereignty</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live proof that no egress occurs. AEGIS-Sentinel probes well-known
            hosts continuously and every blocked attempt is counted.
          </p>
        </div>
        <ProofPanel />
      </div>
    </div>
  );
}