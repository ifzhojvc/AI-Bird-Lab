import { useEffect, useRef, useState } from "react";
import { Alert, Image, Linking, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import type { AcceptedAnalysis } from "../../../shared/contracts";
import { api } from "../api";
import { useAnalysisTask } from "../useAnalysisTask";
import { TaskStatus } from "../components/TaskStatus";
import {
  AudioPlayer,
  Button,
  Result,
  Screen,
  Title,
} from "../components/Common";
import { styles as s } from "../theme";

interface PickedFile {
  uri: string;
  name: string;
  type: string;
  size?: number;
}

function permissionDenied() {
  Alert.alert(
    "Потрібен дозвіл",
    "Дозвольте доступ у налаштуваннях iPhone, щоб скористатися цією функцією.",
    [
      { text: "Скасувати", style: "cancel" },
      { text: "Налаштування", onPress: () => void Linking.openSettings() },
    ],
  );
}

function useUpload(kind: "image" | "audio") {
  const [file, setFile] = useState<PickedFile>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const tracking = useAnalysisTask(kind);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  function choose(value: PickedFile) {
    setFile(value);

    setError("");
  }
  async function submit() {
    if (!file || busy) return;
    if (
      file.size != null &&
      file.size > (kind === "image" ? 20 : 50) * 1024 * 1024
    ) {
      setError("Файл перевищує ліміт: фото до 20 МБ, аудіо до 50 МБ.");
      return;
    }
    const request = new AbortController();
    controller.current = request;
    setBusy(true);
    setError("");

    const body = new FormData();
    body.append("file", {
      uri: file.uri,
      name: file.name,
      type: file.type,
    } as unknown as Blob);
    try {
      tracking.accept(
        await api.request<AcceptedAnalysis>(`/analysis/${kind}`, {
          method: "POST",
          body,
          signal: request.signal,
        }),
      );
    } catch (e) {
      if (!request.signal.aborted) setError((e as Error).message);
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  }
  return { file, choose, busy, error, setError, result: tracking.status?.result, submit, ...tracking };
}

export function PhotoScreen() {
  const upload = useUpload("image");
  const [picking, setPicking] = useState(false);
  async function pick(camera: boolean) {
    setPicking(true);
    try {
      const permission = camera
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        permissionDenied();
        return;
      }
      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ["images"],
        quality: 1,
        allowsEditing: false,
        preferredAssetRepresentationMode:
          ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
      };
      const selected = camera
        ? await ImagePicker.launchCameraAsync(options)
        : await ImagePicker.launchImageLibraryAsync(options);
      if (!selected.canceled && selected.assets[0]) {
        const asset = selected.assets[0];
        const mime = asset.mimeType || "image/jpeg";
        if (!["image/jpeg", "image/png"].includes(mime)) {
          upload.setError(
            "Оберіть JPEG або PNG. Для HEIC експортуйте сумісну копію з Фото.",
          );
          return;
        }
        upload.choose({
          uri: asset.uri,
          name: `bird-${Date.now()}${mime === "image/png" ? ".png" : ".jpg"}`,
          type: mime,
          size: asset.fileSize,
        });
      }
    } catch {
      upload.setError(
        "Не вдалося відкрити камеру або галерею. Перевірте дозволи.",
      );
    } finally {
      setPicking(false);
    }
  }
  return (
    <Screen>
      <Title
        title="Птах у фокусі"
        description="Зробіть фото або оберіть зображення. Результат буде доступний і у веб-лабораторії."
      />
      <View style={s.card}>
        <Button
          title="Зробити фото"
          icon="camera-outline"
          onPress={() => void pick(true)}
          disabled={upload.busy || picking}
          primary
        />
        <Button
          title="Обрати з галереї"
          icon="images-outline"
          onPress={() => void pick(false)}
          disabled={upload.busy || picking}
        />
        <Text style={s.muted}>JPG, JPEG, PNG · до 20 МБ</Text>
      </View>
      {upload.file && (
        <View style={s.card}>
          <Image
            accessibilityLabel="Вибране фото"
            source={{ uri: upload.file.uri }}
            style={s.image}
            resizeMode="contain"
          />
          <Button
            title={
              upload.busy ? "Завантажуємо фотографію…" : "Проаналізувати фото"
            }
            onPress={() => void upload.submit()}
            disabled={upload.busy || picking}
            primary
            icon="scan-outline"
          />
        </View>
      )}
      {upload.busy && (
        <Text accessibilityRole="text" style={s.muted}>
          Завантажуємо файл на сервер. Після прийняття з’явиться стан завдання.
        </Text>
      )}
      {!!upload.error && (
        <Text accessibilityRole="alert" style={s.error}>
          {upload.error}
        </Text>
      )}
      {upload.task && <TaskStatus task={upload.task} status={upload.status} error={upload.taskError} />}
      {upload.result && <Result analysis={upload.result} />}
    </Screen>
  );
}

export function AudioScreen() {
  const upload = useUpload("audio");
  const [picking, setPicking] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY, (status) => {
    if (status.hasError)
      upload.setError("Запис перервано. Спробуйте записати ще раз.");
  });
  const state = useAudioRecorderState(recorder, 250);
  const finish = async () => {
    setTransitioning(true);
    try {
      await recorder.stop();
      await setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,
      });
      if (recorder.uri)
        upload.choose({
          uri: recorder.uri,
          name: `bird-${Date.now()}.m4a`,
          type: "audio/mp4",
        });
    } catch {
      upload.setError("Не вдалося завершити аудіозапис.");
    } finally {
      setTransitioning(false);
    }
  };
  useEffect(() => {
    if (state.isRecording && state.durationMillis >= 59000 && !transitioning)
      void finish();
  }, [state.isRecording, state.durationMillis, transitioning]);
  useEffect(
    () => () => {
      void setAudioModeAsync({ allowsRecording: false }).catch(() => undefined);
    },
    [],
  );
  async function record() {
    if (state.isRecording) {
      await finish();
      return;
    }
    setTransitioning(true);
    try {
      const permission = await requestRecordingPermissionsAsync();
      if (!permission.granted) {
        permissionDenied();
        return;
      }
      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
      });
      await recorder.prepareToRecordAsync();
      recorder.record();
    } catch {
      upload.setError(
        "Не вдалося почати запис. Перевірте доступ до мікрофона.",
      );
    } finally {
      setTransitioning(false);
    }
  }
  async function pick() {
    setPicking(true);
    try {
      const selected = await DocumentPicker.getDocumentAsync({
        type: ["audio/*", "application/ogg"],
        copyToCacheDirectory: true,
        multiple: false,
      });
      if (!selected.canceled && selected.assets[0]) {
        const item = selected.assets[0];
        upload.choose({
          uri: item.uri,
          name: item.name,
          type: item.mimeType || "application/octet-stream",
          size: item.size,
        });
      }
    } catch {
      upload.setError("Не вдалося обрати аудіофайл.");
    } finally {
      setPicking(false);
    }
  }
  return (
    <Screen>
      <Title
        title="Голоси природи"
        description="Оберіть аудіозапис або запишіть спів птаха. До 60 секунд і 50 МБ."
      />
      <View style={s.card}>
        <Button
          title="Обрати аудіофайл"
          icon="folder-open-outline"
          onPress={() => void pick()}
          disabled={
            upload.busy || picking || state.isRecording || transitioning
          }
        />
        <Button
          title={
            state.isRecording
              ? `Зупинити · ${(state.durationMillis / 1000).toFixed(0)} с`
              : "Записати з мікрофона"
          }
          icon={state.isRecording ? "stop-circle-outline" : "mic-outline"}
          primary
          onPress={() => void record()}
          disabled={upload.busy || picking || transitioning}
        />
        <Text style={s.muted}>
          WAV, MP3, FLAC, M4A, AAC, OGG. Запис автоматично завершується через 59
          секунд.
        </Text>
      </View>
      {upload.file && !state.isRecording && (
        <View style={s.card}>
          <Text style={s.text}>{upload.file.name}</Text>
          <AudioPlayer key={upload.file.uri} uri={upload.file.uri} />
          <Button
            title={upload.busy ? "Завантажуємо аудіо…" : "Проаналізувати аудіо"}
            onPress={() => void upload.submit()}
            disabled={upload.busy || transitioning}
            primary
            icon="pulse-outline"
          />
        </View>
      )}
      {!!upload.error && (
        <Text accessibilityRole="alert" style={s.error}>
          {upload.error}
        </Text>
      )}
      {upload.task && <TaskStatus task={upload.task} status={upload.status} error={upload.taskError} />}
      {upload.result && <Result analysis={upload.result} />}
    </Screen>
  );
}
