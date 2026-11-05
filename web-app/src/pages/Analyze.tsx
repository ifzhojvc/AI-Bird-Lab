import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AudioLines, ImagePlus, ScanLine, UploadCloud } from "lucide-react";
import { api, useApi } from "../api";
import type { Entitlement } from "../../../shared/subscriptions";
import { useAuth } from "../auth";
import { PageTitle } from "../components/Common";
import type { AcceptedAnalysis, AcceptedBatchItem } from "../../../shared/contracts";
import { AnalysisTask } from "../components/AnalysisTask";

export default function Analyze({ kind }: { kind: "image" | "audio" }) {
  const access = useApi<Entitlement>("/subscriptions/me");
  const { user } = useAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tasks, setTasks] = useState<AcceptedBatchItem[]>([]);
  const cache = useQueryClient();
  useEffect(() => {
    setFiles([]);
    try {
      const saved = JSON.parse(localStorage.getItem(`bird-tasks:${user?.id}:${api.base}:${kind}`) || "[]") as AcceptedBatchItem[];
      setTasks(Array.isArray(saved) ? saved.filter((item) => typeof item.fileName === "string" && (!item.task || typeof item.task.analysisId === "string")) : []);
    } catch { setTasks([]); }
    setError("");
  }, [kind, user?.id]);
  useEffect(() => {
    if (!files[0]) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(files[0]);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [files]);
  function choose(incoming: File[]) {
    setError("");
    if (incoming.length > 1 && !access.data?.features.includes("batch")) { setError("Пакетний аналіз доступний у PREMIUM. Оберіть одне фото."); return; }

    if (incoming.length > 15) {
      setError("Оберіть не більше 15 фотографій.");
      return;
    }
    if (
      incoming.some(
        (f) =>
          f.size === 0 || f.size > (kind === "image" ? 20 : 50) * 1024 * 1024,
      )
    ) {
      setError("Файл порожній або завеликий. Фото: до 20 МБ; аудіо: до 50 МБ.");
      return;
    }
    setFiles(incoming);
  }
  async function analyze() {
    setBusy(true);
    setError("");

    const body = new FormData();
    const isBatch = files.length > 1;
    files.forEach((f) => body.append(isBatch ? "files" : "file", f));
    try {
      const accepted = isBatch
        ? await api.request<AcceptedBatchItem[]>("/analysis/batch", { method: "POST", body })
        : [{ fileName: files[0].name, task: await api.request<AcceptedAnalysis>(`/analysis/${kind}`, { method: "POST", body }), error: null }];
      setTasks(accepted);
      try { localStorage.setItem(`bird-tasks:${user?.id}:${api.base}:${kind}`, JSON.stringify(accepted)); }
      catch { setError("Завдання прийнято. Браузер не дозволив зберегти його локально; скопіюйте ID для відновлення після перезавантаження."); }
      await cache.invalidateQueries();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="ІНСТРУМЕНТИ ЛАБОРАТОРІЇ"
        title={kind === "image" ? "Птах у фокусі" : "Впізнайте голос природи"}
        text={
          kind === "image"
            ? "Додайте одне фото або до 15 зображень для пакетного аналізу."
            : "Додайте запис до 60 секунд. Модель порівняє звук із 22 класами."
        }
      />
      <div className="analysis-layout">
        <section className="panel">
          <div className="section-title">
            <h2>{kind === "image" ? "Ваші фотографії" : "Ваш аудіозапис"}</h2>
            <span className="step">01 / ЗАВАНТАЖЕННЯ</span>
          </div>
          <label
            className={`upload-zone ${busy ? "disabled" : ""}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!busy)
                choose(
                  Array.from(e.dataTransfer.files).slice(
                    0,
                    kind === "audio" ? 1 : undefined,
                  ),
                );
            }}
          >
            <input
              aria-label="Обрати файли"
              disabled={busy}
              type="file"
              multiple={kind === "image"}
              accept={
                kind === "image"
                  ? ".jpg,.jpeg,.png"
                  : ".wav,.mp3,.flac,.m4a,.aac,.ogg"
              }
              onChange={(e) => choose(Array.from(e.target.files || []))}
            />
            <UploadCloud size={38} />
            <strong>Оберіть файл або перетягніть сюди</strong>
            <span>
              {kind === "image"
                ? "JPG, JPEG, PNG · до 20 МБ кожен"
                : "WAV, MP3, FLAC, M4A, AAC, OGG · до 50 МБ"}
            </span>
            <span className="button">
              Обрати {kind === "image" ? "фотографії" : "аудіо"}
            </span>
          </label>
          {preview && (
            <div className="upload-preview">
              {kind === "image" ? (
                <img src={preview} alt="Попередній перегляд" />
              ) : (
                <audio controls src={preview} />
              )}
              <p>
                {files[0]?.name}
                {files.length > 1 && ` та ще ${files.length - 1} файлів`}
              </p>
            </div>
          )}
          {files.length > 1 && (
            <ul className="file-list">
              {files.map((f, i) => (
                <li key={`${f.name}-${i}`}>
                  {f.name}
                  <span>{(f.size / 1024).toFixed(0)} КБ</span>
                </li>
              ))}
            </ul>
          )}
          <button
            className="primary wide"
            disabled={busy || !files.length}
            onClick={() => void analyze()}
          >
            <ScanLine size={18} />
            {busy
              ? "Завантажуємо файл…"
              : files.length > 1
                ? `Проаналізувати ${files.length} фото`
                : "Розпочати аналіз"}
          </button>
          {busy && (
            <p role="status" className="notice">
              Завантажуємо файл на центральний сервер. Після прийняття відображатиметься стан завдання.
            </p>
          )}
          {error && (
            <p className="error notice" role="alert">
              {error}
            </p>
          )}
        </section>
        <aside className="panel guide">
          {kind === "image" ? (
            <ImagePlus size={32} />
          ) : (
            <AudioLines size={32} />
          )}
          <span className="eyebrow">ТРОХИ ПРО МОДЕЛЬ</span>
          <h2>
            {kind === "image"
              ? "Деталі допомагають впізнати вид"
              : "Прислухайтесь уважніше"}
          </h2>
          <p>
            {kind === "image"
              ? "На фото птах має бути достатньо великим і чітким. Модель ViT навчена на 200 класах CUB."
              : "Wav2Vec2 аналізує короткі сегменти й об’єднує результати за тривалістю. Фоновий звук — окремий клас."}
          </p>
          <div className="guide-number">
            03
            <span>
              найімовірніші класи
              <br />
              для кожного аналізу
            </span>
          </div>
          <p className="caption">
            Модель завжди обирає з відомих класів. Високий confidence не
            гарантує правильність і не замінює експертну перевірку.
          </p>
        </aside>
      </div>
      {tasks.map((item, i) => item.task
        ? <AnalysisTask key={item.task.analysisId} task={item.task} name={item.fileName} expanded={tasks.length === 1} />
        : <p key={i} role="alert" className="error">{item.fileName}: {item.error}</p>)}
    </>
  );
}
