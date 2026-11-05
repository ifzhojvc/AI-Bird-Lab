import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { analysisStatusText, isTerminal, type AcceptedAnalysis, type AnalysisStatus } from "../../../shared/contracts";
import { pollingInterval, watchAnalysis } from "../../../shared/polling";
import { api } from "../api";
import { Result } from "./Common";

export function AnalysisTask({ task, name, expanded = false }: { task: AcceptedAnalysis; name: string; expanded?: boolean }) {
  const [status, setStatus] = useState<AnalysisStatus>();
  const [error, setError] = useState("");
  const cache = useQueryClient();
  useEffect(() => {
    const controller = new AbortController();
    void watchAnalysis(api, task.analysisId, controller.signal, (value) => {
      setStatus(value);
      if (isTerminal(value.status)) void cache.invalidateQueries();
    }, setError, pollingInterval(import.meta.env.VITE_POLL_INTERVAL_MS), () => document.visibilityState !== "hidden");
    return () => controller.abort();
  }, [task.analysisId, cache]);
  const current = status?.status ?? task.status;
  return <section className="panel" data-testid="analysis-task" data-status={current}>
    <strong>{name}</strong>
    <p role="status" aria-live="polite">{!isTerminal(current) && <LoaderCircle size={18} className="spin" />} {analysisStatusText[current]}</p>
    <p className="caption">Завдання {task.analysisId}</p>
    {status?.stalled && <p className="notice">Тривале очікування. Стан збережено; перевірте доступність обробника або зверніться до адміністратора.</p>}
    {error && <p role="alert" className="error">{error} Стан завдання збережено.</p>}
    {status?.errorMessage && <p role="alert" className="error">{status.errorMessage}</p>}
    {status?.result && (expanded ? <Result analysis={status.result} /> : <Link to={`/history/${status.historyId}`}>{status.result.predictedSpecies} · Відкрити результат ↗</Link>)}
  </section>;
}
