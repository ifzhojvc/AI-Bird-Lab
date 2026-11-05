import { useState, type ComponentProps, type ReactNode } from "react";
import {
  ActivityIndicator,
  Image,
  Linking,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAudioPlayer, useAudioPlayerStatus } from "expo-audio";
import {
  birdFields,
  birdName,
  percent,
  analysisStatusText,
  type Analysis,
  type Bird,
} from "../../../shared/contracts";
import { api } from "../api";
import { useLabNavigation } from "../navigation";
import { colors, styles as s } from "../theme";

export function Screen({
  children,
  scroll = true,
}: {
  children: ReactNode;
  scroll?: boolean;
}) {
  return (
    <SafeAreaView style={s.safe} edges={["top", "left", "right"]}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={s.content}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      ) : (
        children
      )}
    </SafeAreaView>
  );
}
export function Button({
  title,
  onPress,
  primary = false,
  disabled = false,
  icon,
}: {
  title: string;
  onPress: () => void;
  primary?: boolean;
  disabled?: boolean;
  icon?: ComponentProps<typeof Ionicons>["name"];
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      accessibilityState={{ disabled }}
      onPress={onPress}
      style={({ pressed }) => [
        s.button,
        primary && s.primary,
        { opacity: disabled ? 0.45 : pressed ? 0.75 : 1 },
      ]}
    >
      {icon && (
        <Ionicons
          name={icon}
          size={19}
          color={primary ? "#142511" : colors.green}
        />
      )}
      <Text style={[s.buttonText, primary && s.primaryText]}>{title}</Text>
    </Pressable>
  );
}
export function State({
  loading,
  error,
  empty,
  retry,
  children,
}: {
  loading?: boolean;
  error?: string;
  empty?: boolean;
  retry?: () => void;
  children?: ReactNode;
}) {
  if (loading)
    return (
      <View style={s.state}>
        <ActivityIndicator color={colors.green} />
        <Text style={s.muted}>Завантажуємо дані…</Text>
      </View>
    );
  if (error)
    return (
      <View style={s.state}>
        <Ionicons name="cloud-offline-outline" color={colors.error} size={30} />
        <Text accessibilityRole="alert" style={s.error}>
          {error}
        </Text>
        {retry && <Button title="Спробувати ще раз" onPress={retry} />}
      </View>
    );
  if (empty)
    return (
      <View style={s.state}>
        <Ionicons name="leaf-outline" color={colors.green} size={35} />
        <Text style={s.h2}>Нове відкриття попереду</Text>
        <Text style={s.muted}>
          Ще немає спостережень. Додайте фото або аудіо.
        </Text>
      </View>
    );
  return <>{children}</>;
}
export function Title({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <View style={{ gap: 10 }}>
      <Text style={s.eyebrow}>AI BIRD LAB / ЛАБОРАТОРІЯ</Text>
      <Text style={s.title}>{title}</Text>
      <Text style={s.subtitle}>{description}</Text>
    </View>
  );
}
export function AudioPlayer({ uri }: { uri: string }) {
  const player = useAudioPlayer({ uri, headers: api.authHeaders() });
  const status = useAudioPlayerStatus(player);
  const [error, setError] = useState("");
  async function toggle() {
    try {
      if (status.playing) player.pause();
      else {
        if (status.didJustFinish) await player.seekTo(0);
        player.play();
      }
      setError("");
    } catch {
      setError("Не вдалося відтворити запис.");
    }
  }
  return (
    <View style={{ gap: 8 }}>
      <Button
        title={status.playing ? "Призупинити" : "Відтворити запис"}
        icon={status.playing ? "pause" : "play"}
        onPress={() => void toggle()}
      />
      <Text style={s.muted}>
        {status.currentTime.toFixed(0)} / {status.duration.toFixed(0)} с
      </Text>
      {!!error && <Text style={s.error}>{error}</Text>}
    </View>
  );
}
export function BirdInfo({ bird }: { bird: Bird }) {
  return (
    <View style={s.card}>
      <Text style={s.h2}>{bird.ukrainianName || bird.commonName}</Text>
      <Text style={s.muted}>{bird.scientificName}</Text>
      {birdFields.map(([field, label]) => (
        <View key={field} style={s.divider}>
          <Text style={s.muted}>{label}</Text>
          <Text style={s.text}>
            {String(bird[field] || "Немає перевірених даних")}
          </Text>
        </View>
      ))}
      {bird.sources.map((url, i) => (
        <Pressable
          accessibilityRole="link"
          key={url}
          onPress={() => void Linking.openURL(url)}
        >
          <Text style={s.link}>Джерело {i + 1} ↗</Text>
        </Pressable>
      ))}
    </View>
  );
}
export function Result({ analysis: a }: { analysis: Analysis }) {
  const navigation = useLabNavigation();
  if (a.status !== "Completed") return <Text style={s.muted}>{analysisStatusText[a.status]}</Text>;
  return (
    <View style={{ gap: 18 }}>
      <View style={s.card}>
        <Text style={s.badge}>ЗБЕРЕЖЕНО В СПІЛЬНІЙ ІСТОРІЇ · № {a.id}</Text>
        <Text style={s.h2}>{birdName(a)}</Text>
        <Text style={s.muted}>{a.description}</Text>
        {a.predictions.map((p) => (
          <View key={p.rank} style={s.divider}>
            <View style={[s.row, { justifyContent: "space-between" }]}>
              <Text style={[s.text, { flex: 1 }]}>
                {p.rank}. {p.speciesName}
              </Text>
              <Text style={s.link}>{percent(p.confidence)}</Text>
            </View>
            <Text style={s.muted}>
              {p.scientificName || "Наукову назву не зіставлено"}
            </Text>
            <View style={s.meter}>
              <View
                style={[s.meterFill, { width: `${p.confidence * 100}%` }]}
              />
            </View>
          </View>
        ))}
        <Text style={s.muted}>
          Confidence — впевненість моделі, а не виміряна точність.
        </Text>
        <Text selectable style={[s.muted, { fontSize: 10 }]}>
          {a.modelName}
          {"\n"}
          {a.modelRevision}
        </Text>
        <Button
          title="Відкрити аналіз"
          onPress={() => navigation.navigate("Analysis", { id: a.id })}
          icon="open-outline"
        />
      </View>
      {a.bird ? (
        <>
          <Button
            title="Картка виду"
            onPress={() => navigation.navigate("Bird", { id: a.bird!.id })}
            icon="leaf-outline"
          />
          <BirdInfo bird={a.bird} />
        </>
      ) : (
        <Text style={s.muted}>Перевіреної довідки для цього класу немає.</Text>
      )}
    </View>
  );
}
export function AnalysisCard({
  analysis: a,
  gallery = false,
}: {
  analysis: Analysis;
  gallery?: boolean;
}) {
  const navigation = useLabNavigation();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => navigation.navigate("Analysis", { id: a.id })}
      style={s.flatCard}
    >
      {(gallery || a.analysisType === "image") && (
        <Image
          accessibilityLabel={birdName(a)}
          source={{ uri: api.file(a.fileUrl), headers: api.authHeaders() }}
          style={s.media}
          resizeMode="cover"
        />
      )}
      <View style={{ padding: 17, gap: 7 }}>
        <Text style={s.badge}>
          {a.analysisType === "image" ? "ФОТО" : "АУДІО"} · №{a.id} ·{" "}
          {new Date(a.analysisDate).toLocaleDateString("uk-UA")}
        </Text>
        <Text style={s.h2}>{birdName(a)}</Text>
        <Text style={s.muted}>
          {a.bird?.scientificName || a.predictedSpecies}
        </Text>
        <View style={[s.row, { justifyContent: "space-between" }]}>
          <Text style={s.muted}>Confidence</Text>
          <Text style={s.link}>{percent(a.confidence)}</Text>
        </View>
        <View style={s.meter}>
          <View style={[s.meterFill, { width: `${a.confidence * 100}%` }]} />
        </View>
      </View>
    </Pressable>
  );
}
