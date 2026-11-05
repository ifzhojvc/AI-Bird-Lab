import { useState } from "react";
import { Text, View } from "react-native";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { api, useRemote } from "../api";
import { useLabNavigation } from "../navigation";
import { Button, Screen, Title } from "../components/Common";
import { styles as s } from "../theme";

export default function InfoScreen() {
  const navigation = useLabNavigation();
  const health = useRemote<{ status: string }>("/health");
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  async function exportCsv() {
    setExporting(true);
    setError("");
    try {
      if (!api.base) throw new Error("Налаштуйте EXPO_PUBLIC_API_URL.");
      if (!(await Sharing.isAvailableAsync()))
        throw new Error(
          "Спільний доступ до файлів недоступний на цьому пристрої.",
        );
      const file = await File.downloadFileAsync(
        `${api.base}/api/export/csv`,
        new File(Paths.cache, "bird_analysis.csv"),
        { idempotent: true, headers: api.authHeaders() },
      );
      await Sharing.shareAsync(file.uri, {
        mimeType: "text/csv",
        UTI: "public.comma-separated-values-text",
        dialogTitle: "Експорт історії AI Bird Lab",
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setExporting(false);
    }
  }
  return (
    <Screen>
      <Title
        title="Ваша лабораторія"
        description="Ваші спостереження на телефоні та у вебі. Доступні можливості визначає сервер за активним тарифом."
      />
      <View style={s.card}>
        <Button title="Мій тариф і платежі" icon="person-circle-outline" onPress={() => navigation.navigate("Subscription")} primary />
        <Button
          title="Галерея"
          icon="images-outline"
          onPress={() => navigation.navigate("Gallery")}
        />
        <Button
          title="Статистика"
          icon="stats-chart-outline"
          onPress={() => navigation.navigate("Statistics")}
        />
        <Button
          title="Порівняння видів і моделей"
          icon="git-compare-outline"
          onPress={() => navigation.navigate("Compare")}
        />
        <Button
          title={exporting ? "Готуємо CSV…" : "Експортувати CSV"}
          icon="download-outline"
          onPress={() => void exportCsv()}
          disabled={exporting}
        />
        {!!error && <Text style={s.error}>{error}</Text>}
      </View>
      <View style={s.card}>
        <Text style={s.h2}>Підключення</Text>
        <Text style={s.muted}>Центральний API</Text>
        <Text selectable style={s.text}>
          {api.base ||
            "Задайте EXPO_PUBLIC_API_URL в mobile-app/.env. localhost на iPhone не підтримується."}
        </Text>
        <Text style={health.data ? s.link : s.error}>
          {health.data
            ? "Сервіси доступні"
            : health.error || "Перевіряємо з’єднання…"}
        </Text>
        <Button
          title="Перевірити з’єднання"
          onPress={() => void health.reload()}
        />
      </View>
      <View style={s.card}>
        <Text style={s.h2}>Про AI Bird Lab</Text>
        <Text style={s.muted}>
          Фото: PwNzDust/vit_cub, 200 класів. Аудіо:
          greenarcade/wav2vec2-vd-bird-sound-classification, 22 класи з фоновим
          звуком.
        </Text>
        <Text style={s.muted}>
          Усі аналізи проходять через ASP.NET Core та зберігаються в SQL Server.
          Python виконує класифікацію. Confidence не є оцінкою загальної
          точності.
        </Text>
      </View>
    </Screen>
  );
}
