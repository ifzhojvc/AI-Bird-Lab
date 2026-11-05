import { useEffect, useState } from "react";
import { AppState } from "react-native";
import { useIsFocused } from "@react-navigation/native";
import { File, Paths } from "expo-file-system";
import { type AcceptedAnalysis, type AnalysisStatus } from "../../shared/contracts";
import { pollingInterval, watchAnalysis } from "../../shared/polling";
import { api } from "./api";

export function useAnalysisTask(kind: "image" | "audio") {
  const [task, setTask] = useState<AcceptedAnalysis | undefined>(() => {
    try {
      const file = new File(Paths.document, `bird-task-${kind}.json`);
      const saved = file.exists ? JSON.parse(file.textSync()) : null;
      return saved?.base === api.base && typeof saved?.task?.analysisId === "string" ? saved.task : undefined;
    } catch { return undefined; }
  });
  const [status, setStatus] = useState<AnalysisStatus>();
  const [error, setError] = useState("");
  const [active, setActive] = useState(AppState.currentState === "active");
  const focused = useIsFocused();
  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => setActive(state === "active"));
    return () => subscription.remove();
  }, []);
  useEffect(() => {
    if (!task || !active || !focused) return;
    const controller = new AbortController();
    void watchAnalysis(api, task.analysisId, controller.signal, setStatus, setError, pollingInterval(process.env.EXPO_PUBLIC_POLL_INTERVAL_MS));
    return () => controller.abort();
  }, [task?.analysisId, active, focused]);
  function accept(value: AcceptedAnalysis) {
    setTask(value);
    setStatus(undefined);
    setError("");
    try { new File(Paths.document, `bird-task-${kind}.json`).write(JSON.stringify({ base: api.base, task: value })); }
    catch { setError("Завдання прийнято, але ID не вдалося зберегти на пристрої. Скопіюйте його для відновлення."); }
  }
  return { task, status, taskError: error, accept };
}
