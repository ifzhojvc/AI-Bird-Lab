import { Text, View } from "react-native";
import {
  percent,
  type Summary,
  type SpeciesCount,
  type ConfidenceBin,
  type EvaluationStats,
} from "../../../shared/contracts";
import { useRemote } from "../api";
import { Screen, State, Title } from "../components/Common";
import { styles as s } from "../theme";
import type { Entitlement } from "../../../shared/subscriptions";

export default function StatisticsScreen() {
  const access = useRemote<Entitlement>("/subscriptions/me");
  const summary = useRemote<Summary>("/statistics/summary");
  const species = useRemote<SpeciesCount[]>("/statistics/species");
  const bins = useRemote<ConfidenceBin[]>("/statistics/confidence");
  const evaluations = useRemote<EvaluationStats[]>(access.data?.features.includes("advancedStatistics") ? "/statistics/evaluations" : null);
  const max = Math.max(1, ...(species.data?.map((x) => x.count) || []));
  return (
    <Screen>
      <Title
        title="Статистика"
        description="Показники спільної бази. Confidence показує впевненість моделі, а не її точність."
      />
      <State
        loading={summary.loading && !summary.data}
        error={
          summary.error || species.error || bins.error || evaluations.error
        }
        empty={summary.data?.totalAnalyses === 0}
        retry={() => {
          void summary.reload();
          void species.reload();
          void bins.reload();
          void evaluations.reload();
        }}
      >
        <View style={s.wrap}>
          {[
            ["Фото", summary.data?.imageAnalyses],
            ["Аудіо", summary.data?.audioAnalyses],
            ["Мін. confidence", percent(summary.data?.minConfidence)],
            ["Макс. confidence", percent(summary.data?.maxConfidence)],
          ].map(([name, value]) => (
            <View key={name} style={s.metric}>
              <Text style={s.metricValue}>{value}</Text>
              <Text style={s.muted}>{name}</Text>
            </View>
          ))}
        </View>
        <View style={s.card}>
          <Text style={s.h2}>Популярні передбачення</Text>
          {species.data?.slice(0, 10).map((x) => (
            <View key={x.species} style={{ gap: 7 }}>
              <View style={[s.row, { justifyContent: "space-between" }]}>
                <Text style={[s.text, { flex: 1 }]}>{x.species}</Text>
                <Text style={s.link}>{x.count}</Text>
              </View>
              <View style={s.meter}>
                <View
                  style={[s.meterFill, { width: `${(x.count / max) * 100}%` }]}
                />
              </View>
            </View>
          ))}
        </View>
        <View style={s.card}>
          <Text style={s.h2}>Розподіл confidence</Text>
          {bins.data?.map((x) => (
            <View key={x.label} style={s.divider}>
              <Text style={s.text}>
                {x.label} · {x.count} аналізів
              </Text>
              <View style={s.meter}>
                <View
                  style={[
                    s.meterFill,
                    {
                      width: `${(x.count / Math.max(1, summary.data?.totalAnalyses || 0)) * 100}%`,
                    },
                  ]}
                />
              </View>
            </View>
          ))}
        </View>
        <View style={s.card}>
          <Text style={s.h2}>Перевірені еталони</Text>
          <Text style={s.muted}>
            Лише розмічені зразки. Це не загальна точність моделі.
          </Text>
          {evaluations.data?.length ? (
            evaluations.data.map((e) => (
              <View key={`${e.model}-${e.experiment}`} style={s.divider}>
                <Text style={s.text}>{e.model}</Text>
                <Text style={s.muted}>
                  {e.experiment}: {e.samples} зразків. TOP-1 {e.top1Correct}/
                  {e.samples}, TOP-3 {e.top3Correct}/{e.samples}.
                </Text>
              </View>
            ))
          ) : (
            <Text style={s.muted}>Немає оцінених еталонних зразків.</Text>
          )}
        </View>
      </State>
    </Screen>
  );
}
