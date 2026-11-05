import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowUpRight,
  Bird as BirdIcon,
  LoaderCircle,
  Mic,
} from "lucide-react";
import { api } from "../api";
import {
  birdFields,
  birdName,
  percent,
  analysisStatusText,
  type Analysis,
  type Bird,
} from "../../../shared/contracts";

export function State({
  loading,
  error,
  empty,
  retry,
  children,
}: {
  loading?: boolean;
  error?: Error | null;
  empty?: boolean;
  retry?: () => void;
  children: ReactNode;
}) {
  if (loading)
    return (
      <div className="state" role="status">
        <LoaderCircle className="spin" />
        <p>Завантажуємо дані…</p>
      </div>
    );
  if (error)
    return (
      <div className="state error" role="alert">
        <AlertCircle />
        <p>{error.message}</p>
        {retry && <button onClick={retry}>Спробувати ще раз</button>}
      </div>
    );
  if (empty)
    return (
      <div className="state">
        <BirdIcon size={36} />
        <h3>Тут починається ваше дослідження</h3>
        <p>Поки немає результатів. Завантажте фото або аудіозапис птаха.</p>
        <Link className="button" to="/photo">
          Проаналізувати фото <ArrowUpRight size={17} />
        </Link>
      </div>
    );
  return <>{children}</>;
}
export function PageTitle({
  eyebrow,
  title,
  text,
  action,
}: {
  eyebrow: string;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-title">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
      {action}
    </header>
  );
}
export function AnalysisCard({ analysis: a }: { analysis: Analysis }) {
  return (
    <Link className="analysis-card" to={`/history/${a.id}`}>
      <div className="card-image">
        {a.analysisType === "image" ? (
          <img src={api.file(a.fileUrl)} alt={birdName(a)} loading="lazy" />
        ) : (
          <div className="audio-art">
            <Mic size={45} />
            <span>Аудіоспостереження</span>
          </div>
        )}
        <span className="media-badge">
          {a.analysisType === "image" ? "Фото" : "Аудіо"}
        </span>
      </div>
      <div className="card-body">
        <div className="card-top">
          <span className="caption">
            № {a.id} · {new Date(a.analysisDate).toLocaleDateString("uk-UA")}
          </span>
          <ArrowUpRight size={17} />
        </div>
        <h3>{birdName(a)}</h3>
        <p className="latin">{a.bird?.scientificName || a.predictedSpecies}</p>
        <div className="confidence-line">
          <span>Confidence</span>
          <strong>{percent(a.confidence)}</strong>
        </div>
        <div className="meter">
          <span style={{ width: `${a.confidence * 100}%` }} />
        </div>
      </div>
    </Link>
  );
}
export function BirdInfo({ bird }: { bird: Bird }) {
  return (
    <section className="panel">
      <div className="section-title">
        <h2>{bird.ukrainianName || bird.commonName}</h2>
        <Link to={`/birds/${bird.id}`}>
          Картка виду <ArrowUpRight size={16} />
        </Link>
      </div>
      <p className="latin">
        {bird.scientificName} · {bird.commonName}
      </p>
      <dl className="bird-data">
        {birdFields.map(([field, label]) => (
          <div key={field}>
            <dt>{label}</dt>
            <dd>{String(bird[field] || "Немає перевірених даних")}</dd>
          </div>
        ))}
      </dl>
      <div className="source-links">
        {bird.sources.map((url, i) => (
          <a key={url} href={url} target="_blank" rel="noreferrer">
            Джерело {i + 1} <ArrowUpRight size={14} />
          </a>
        ))}
      </div>
    </section>
  );
}
export function Result({ analysis: a }: { analysis: Analysis }) {
  if (a.status !== "Completed") return <p role="status" className="notice">{analysisStatusText[a.status]}</p>;
  return (
    <div className="result-stack">
      <section className="panel result">
        <span className="eyebrow">Результат аналізу № {a.id}</span>
        <h2>{birdName(a)}</h2>
        <p>{a.description}</p>
        <div className="predictions">
          {a.predictions.map((p) => (
            <div key={p.rank}>
              <span className="rank">0{p.rank}</span>
              <div>
                <strong>{p.speciesName}</strong>
                <small>
                  {p.scientificName || "Наукову назву не зіставлено"}
                </small>
                <div className="meter">
                  <span style={{ width: `${p.confidence * 100}%` }} />
                </div>
              </div>
              <b>{percent(p.confidence)}</b>
            </div>
          ))}
        </div>
        <p className="caption">
          Confidence — впевненість моделі, а не виміряна точність. Аналіз:{" "}
          {a.elapsedSeconds.toFixed(2)} с.
        </p>
        <details>
          <summary>Модель та походження результату</summary>
          <p className="mono">
            {a.modelName}
            <br />
            {a.modelRevision}
          </p>
        </details>
        <Link to={`/history/${a.id}`} className="text-link">
          Відкрити збережений аналіз <ArrowUpRight size={16} />
        </Link>
      </section>
      {a.bird ? (
        <BirdInfo bird={a.bird} />
      ) : (
        <p className="notice">
          Для цього класу немає перевіреної картки виду. Висновок моделі
          збережено без вигаданої довідкової інформації.
        </p>
      )}
    </div>
  );
}
