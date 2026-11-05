import { ActivityIndicator, Text, View } from "react-native";
import { analysisStatusText, isTerminal, type AcceptedAnalysis, type AnalysisStatus } from "../../../shared/contracts";
import { styles as s, colors } from "../theme";
import { Button } from "./Common";
import { useLabNavigation } from "../navigation";

export function TaskStatus({ task, status, error }: { task: AcceptedAnalysis; status?: AnalysisStatus; error: string }) {
  const navigation = useLabNavigation();
  const current = status?.status ?? task.status;
  return <View style={s.card} testID="analysis-task">
    {!isTerminal(current) && <ActivityIndicator color={colors.green} />}
    <Text accessibilityLiveRegion="polite" style={s.h2}>{analysisStatusText[current]}</Text>
    <Text selectable style={s.muted}>Завдання {task.analysisId}</Text>
    {status?.stalled && <Text style={s.muted}>Тривале очікування. Завдання збережено на сервері. Перевірте стан обробника.</Text>}
    {!!error && <Text accessibilityRole="alert" style={s.error}>{error}</Text>}
    {!!status?.errorMessage && <Text accessibilityRole="alert" style={s.error}>{status.errorMessage}</Text>}
    {current === "Completed" && <Button title="Відкрити результат в історії" onPress={() => navigation.navigate("Analysis", { id: status?.historyId ?? task.historyId })} />}
  </View>;
}
