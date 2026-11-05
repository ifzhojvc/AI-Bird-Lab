import { useState } from "react";
import { Alert, Image, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { Analysis, Bird } from "../../../shared/contracts";
import { birdName } from "../../../shared/contracts";
import { api, useRemote } from "../api";
import {
  AudioPlayer,
  BirdInfo,
  Button,
  Result,
  Screen,
  State,
  Title,
} from "../components/Common";
import type { RootStack } from "../navigation";
import { styles as s } from "../theme";

export function AnalysisScreen({
  route,
  navigation,
}: NativeStackScreenProps<RootStack, "Analysis">) {
  const query = useRemote<Analysis>(`/analyses/${route.params.id}`);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    setBusy(true);
    try {
      await api.request(`/analyses/${route.params.id}`, { method: "DELETE" });
      navigation.navigate("Tabs", { screen: "History" });
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <Screen>
      <Title
        title={`Аналіз № ${route.params.id}`}
        description={
          query.data
            ? `${query.data.originalFileName} · ${new Date(query.data.analysisDate).toLocaleString("uk-UA")}`
            : "Збережене спостереження"
        }
      />
      <State
        loading={query.loading && !query.data}
        error={query.error}
        retry={() => void query.reload()}
      >
        {query.data && (
          <>
            <View style={s.card}>
              {query.data.analysisType === "image" ? (
                <Image
                  accessibilityLabel={birdName(query.data)}
                  source={{ uri: api.file(query.data.fileUrl), headers: api.authHeaders() }}
                  style={s.image}
                  resizeMode="contain"
                />
              ) : (
                <AudioPlayer uri={api.file(query.data.fileUrl)} />
              )}
            </View>
            <Result analysis={query.data} />
            {query.data.evaluation && (
              <View style={s.card}>
                <Text style={s.h2}>Розмічений зразок</Text>
                <Text style={s.text}>
                  Еталон: {query.data.evaluation.expectedLabel}
                </Text>
                <Text style={s.muted}>
                  TOP-1:{" "}
                  {query.data.evaluation.top1Correct ? "збіг" : "не збігається"}
                  . TOP-3:{" "}
                  {query.data.evaluation.top3Correct ? "збіг" : "не збігається"}
                  .
                </Text>
              </View>
            )}
            <Button
              title={busy ? "Видаляємо…" : "Видалити аналіз"}
              disabled={busy}
              icon="trash-outline"
              onPress={() =>
                Alert.alert(
                  "Видалити спостереження?",
                  "Буде видалено запис і його серверний файл для всіх пристроїв.",
                  [
                    { text: "Скасувати", style: "cancel" },
                    {
                      text: "Видалити",
                      style: "destructive",
                      onPress: () => void remove(),
                    },
                  ],
                )
              }
            />
          </>
        )}
      </State>
      {!!error && <Text style={s.error}>{error}</Text>}
    </Screen>
  );
}

export function BirdScreen({
  route,
}: NativeStackScreenProps<RootStack, "Bird">) {
  const query = useRemote<Bird>(`/birds/${route.params.id}`);
  return (
    <Screen>
      <Title
        title="Картка птаха"
        description="Перевірена довідкова інформація та джерела."
      />
      <State
        loading={query.loading && !query.data}
        error={query.error}
        retry={() => void query.reload()}
      >
        {query.data && <BirdInfo bird={query.data} />}
      </State>
    </Screen>
  );
}
