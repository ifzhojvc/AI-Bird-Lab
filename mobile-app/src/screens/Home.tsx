import { Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRemote } from "../api";
import { useLabNavigation } from "../navigation";
import {
  AnalysisCard,
  Button,
  Screen,
  State,
  Title,
} from "../components/Common";
import { colors, styles as s } from "../theme";
import type { Analysis, Page, Summary } from "../../../shared/contracts";

export default function HomeScreen() {
  const summary = useRemote<Summary>("/statistics/summary");
  const recent = useRemote<Page<Analysis>>("/analyses?pageSize=4");
  const navigation = useLabNavigation();
  return (
    <Screen>
      <Title
        title="Світ птахів поруч."
        description="Ваша польова лабораторія. Нові відкриття починаються з уважного спостереження."
      />
      <View style={[s.card, { backgroundColor: "#1e321f", padding: 23 }]}>
        <Ionicons name="leaf-outline" size={37} color={colors.green} />
        <Text style={[s.h2, { fontSize: 25 }]}>
          Побачили птаха?{"\n"}Дізнайтеся більше.
        </Text>
        <Text style={s.subtitle}>
          Фотографія або голос — дві моделі допоможуть розпізнати вид.
        </Text>
        <Button
          title="Аналізувати фото"
          primary
          icon="camera-outline"
          onPress={() => navigation.navigate("Tabs", { screen: "Photo" })}
        />
        <Button
          title="Розпізнати голос"
          icon="musical-notes-outline"
          onPress={() => navigation.navigate("Tabs", { screen: "Audio" })}
        />
      </View>
      <State
        loading={summary.loading && !summary.data}
        error={summary.error}
        retry={() => void summary.reload()}
      >
        <View style={s.wrap}>
          {[
            ["Усього аналізів", summary.data?.totalAnalyses],
            ["Видів зіставлено", summary.data?.identifiedSpecies],
            ["Фотоаналізів", summary.data?.imageAnalyses],
            ["Аудіоаналізів", summary.data?.audioAnalyses],
          ].map(([label, value]) => (
            <View style={s.metric} key={String(label)}>
              <Text style={s.metricValue}>{value ?? 0}</Text>
              <Text style={s.muted}>{label}</Text>
            </View>
          ))}
        </View>
      </State>
      <View style={[s.row, { justifyContent: "space-between" }]}>
        <Text style={s.h2}>Останні відкриття</Text>
        <Button
          title="Усі"
          onPress={() => navigation.navigate("Tabs", { screen: "History" })}
        />
      </View>
      <State
        loading={recent.loading && !recent.data}
        error={recent.error}
        empty={recent.data?.total === 0}
        retry={() => void recent.reload()}
      >
        <View style={{ marginHorizontal: -20 }}>
          {recent.data?.items.map((a) => (
            <AnalysisCard key={a.id} analysis={a} />
          ))}
        </View>
      </State>
      <Text style={s.muted}>
        AI допомагає визначити вид. Висновок потребує перевірки, особливо поза
        класами моделей.
      </Text>
    </Screen>
  );
}
