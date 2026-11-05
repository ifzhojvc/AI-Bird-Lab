import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  Camera,
  Fingerprint,
  ScanLine,
  Bird,
  Database,
} from "lucide-react";
import { useApi, api } from "../api";
import { AnalysisCard, State } from "../components/Common";
import type { Analysis, Page, Summary } from "../../../shared/contracts";

export default function Home() {
  const summary = useApi<Summary>("/statistics/summary");
  const recent = useApi<Page<Analysis>>("/analyses?pageSize=6");
  const image = recent.data?.items.find((a) => a.analysisType === "image");
  return (
    <>
      <div className="welcome">
        <span className="eyebrow">
          <span className="status-dot" /> ВАША ЦИФРОВА ПОЛЬОВА ЛАБОРАТОРІЯ
        </span>
        <span className="caption">
          Спостерігайте. Впізнавайте. Досліджуйте.
        </span>
      </div>
      <section className="hero">
        <div className="hero-copy">
          <span className="pill">
            <Fingerprint size={15} /> ПРИРОДА × ШТУЧНИЙ ІНТЕЛЕКТ
          </span>
          <h1>
            Відкрийте світ
            <br />
            птахів <em>поруч.</em>
          </h1>
          <p>
            Перетворюйте фотографії та спів на нові відкриття. Дві AI-моделі,
            одна лабораторія — на комп’ютері та у вашій кишені.
          </p>
          <div className="actions">
            <Link className="button primary" to="/photo">
              <Camera size={18} /> Аналізувати фото <ArrowUpRight size={17} />
            </Link>
            <Link className="button" to="/audio">
              <AudioLines size={18} /> Розпізнати голос
            </Link>
          </div>
          <div className="hero-foot">
            <span>
              <ScanLine size={15} /> TOP-3 передбачення
            </span>
            <span>
              <Database size={15} /> Спільна історія
            </span>
          </div>
        </div>
        <div className="hero-visual">
          {image ? (
            <img
              src={api.file(image.fileUrl)}
              alt="Останнє фото у вашій лабораторії"
            />
          ) : (
            <Bird size={150} strokeWidth={0.7} />
          )}
          <div className="scan-corner top" />
          <div className="scan-corner bottom" />
          <div className="visual-tag">
            <span className="status-dot" />
            <span>
              {image
                ? image.bird?.scientificName || image.predictedSpecies
                : "Готові до першого спостереження"}
              <small>
                {image
                  ? `Спостереження № ${image.id} · з вашої історії`
                  : "Завантажте своє фото"}
              </small>
            </span>
          </div>
          <span className="visual-index">FIELD NOTES / AI BIRD LAB</span>
        </div>
      </section>
      <State
        loading={summary.isLoading}
        error={summary.error}
        retry={() => void summary.refetch()}
      >
        <section className="metrics">
          {[
            [summary.data?.totalAnalyses, "Усього аналізів", ScanLine],
            [summary.data?.identifiedSpecies, "Видів зіставлено", Bird],
            [summary.data?.imageAnalyses, "Фотоаналізів", Camera],
            [summary.data?.audioAnalyses, "Аудіоаналізів", AudioLines],
          ].map(([value, label, Icon]) => {
            const Glyph = Icon as typeof Bird;
            return (
              <div className="metric" key={String(label)}>
                <Glyph size={19} />
                <strong>{(value as number) ?? 0}</strong>
                <span>{label as string}</span>
              </div>
            );
          })}
        </section>
      </State>
      <div className="section-title">
        <div>
          <span className="eyebrow">ЖУРНАЛ СПОСТЕРЕЖЕНЬ</span>
          <h2>Останні відкриття</h2>
        </div>
        <Link to="/history">
          Уся історія <ArrowRight size={17} />
        </Link>
      </div>
      <State
        loading={recent.isLoading}
        error={recent.error}
        empty={recent.data?.items.length === 0}
        retry={() => void recent.refetch()}
      >
        <div className="gallery-grid">
          {recent.data?.items.map((a) => (
            <AnalysisCard key={a.id} analysis={a} />
          ))}
        </div>
      </State>
      <div className="research-note">
        <Bird size={24} />
        <div>
          <strong>Кожне спостереження має значення.</strong>
          <p>
            AI допомагає досліджувати природу. Остаточне визначення виду
            потребує перевірки — особливо за межами наборів класів моделей.
          </p>
        </div>
        <Link to="/compare">
          <ArrowUpRight size={22} />
        </Link>
      </div>
    </>
  );
}
