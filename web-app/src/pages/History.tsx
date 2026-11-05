import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowUpRight,
  Download,
  Search,
  Trash2,
} from "lucide-react";
import { api, useApi } from "../api";
import {
  AnalysisCard,
  BirdInfo,
  PageTitle,
  Result,
  State,
} from "../components/Common";
import {
  birdName,
  percent,
  type Analysis,
  type Bird,
  type Page,
} from "../../../shared/contracts";

export function History({ gallery = false }: { gallery?: boolean }) {
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [sort, setSort] = useState("date_desc");
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({
    page: String(page),
    pageSize: gallery ? "12" : "15",
    search,
    sort,
    analysisType: gallery ? "image" : kind,
  });
  const query = useApi<Page<Analysis>>(`/analyses${gallery ? "/gallery" : ""}?${params}`);
  return (
    <>
      <PageTitle
        eyebrow="ВАШІ СПОСТЕРЕЖЕННЯ"
        title={gallery ? "Галерея птахів" : "Моя історія"}
        text="Фото з телефона та результати з вебу зберігаються в одній лабораторії."
        action={
          <a className="button" href={`${api.base}/api/export/csv`}>
            <Download size={17} /> Експорт CSV
          </a>
        }
      />
      <div className="filters">
        <label className="search">
          <Search size={18} />
          <input
            aria-label="Пошук аналізів"
            value={search}
            placeholder="Назва виду або файлу…"
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </label>
        {!gallery && (
          <select
            aria-label="Тип аналізу"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Усі типи</option>
            <option value="image">Фотографії</option>
            <option value="audio">Аудіозаписи</option>
          </select>
        )}
        <select
          aria-label="Сортування"
          value={sort}
          onChange={(e) => {
            setSort(e.target.value);
            setPage(1);
          }}
        >
          <option value="date_desc">Спочатку нові</option>
          <option value="date_asc">Спочатку старі</option>
          <option value="confidence_desc">За confidence</option>
          <option value="species">За назвою виду</option>
        </select>
      </div>
      <State
        loading={query.isLoading}
        error={query.error}
        empty={query.data?.total === 0}
        retry={() => void query.refetch()}
      >
        {gallery ? (
          <div className="gallery-grid">
            {query.data?.items.map((a) => (
              <AnalysisCard key={a.id} analysis={a} />
            ))}
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Спостереження</th>
                  <th>Тип</th>
                  <th>Confidence</th>
                  <th>Дата</th>
                  <th>
                    <span className="sr-only">Деталі</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {query.data?.items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Link to={`/history/${a.id}`}>
                        <strong>{birdName(a)}</strong>
                        <small>{a.originalFileName}</small>
                      </Link>
                    </td>
                    <td>
                      <span className="pill">
                        {a.analysisType === "image" ? "Фото" : "Аудіо"}
                      </span>
                    </td>
                    <td className="green">{percent(a.confidence)}</td>
                    <td>{new Date(a.analysisDate).toLocaleString("uk-UA")}</td>
                    <td>
                      <Link
                        aria-label={`Деталі аналізу ${a.id}`}
                        to={`/history/${a.id}`}
                      >
                        <ArrowUpRight size={18} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {query.data && query.data.total > 0 && (
          <div className="pagination">
            <span>
              {query.data.total} записів · сторінка {page} з{" "}
              {Math.ceil(query.data.total / query.data.pageSize)}
            </span>
            <div>
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Назад
              </button>
              <button
                disabled={page * query.data.pageSize >= query.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Далі
              </button>
            </div>
          </div>
        )}
      </State>
    </>
  );
}

export function AnalysisDetails() {
  const { id } = useParams();
  const query = useApi<Analysis>(`/analyses/${id}`);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const cache = useQueryClient();
  async function remove() {
    if (!window.confirm("Видалити цей аналіз і його серверний файл?")) return;
    setRemoving(true);
    try {
      await api.request(`/analyses/${id}`, { method: "DELETE" });
      await cache.invalidateQueries();
      navigate("/history");
    } catch (e) {
      setError((e as Error).message);
      setRemoving(false);
    }
  }
  return (
    <>
      <Link className="text-link" to="/history">
        <ArrowLeft size={16} /> До історії
      </Link>
      <PageTitle
        eyebrow="ЗБЕРЕЖЕНЕ СПОСТЕРЕЖЕННЯ"
        title={`Аналіз № ${id}`}
        text={
          query.data
            ? `${query.data.originalFileName} · ${new Date(query.data.analysisDate).toLocaleString("uk-UA")}`
            : "Завантаження спостереження"
        }
        action={
          <button
            className="danger"
            disabled={removing || !query.data}
            onClick={() => void remove()}
          >
            <Trash2 size={16} /> Видалити
          </button>
        }
      />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <State
        loading={query.isLoading}
        error={query.error}
        retry={() => void query.refetch()}
      >
        {query.data && (
          <>
            <div className="detail-media">
              {query.data.analysisType === "image" ? (
                <img
                  src={api.file(query.data.fileUrl)}
                  alt={birdName(query.data)}
                />
              ) : (
                <audio controls src={api.file(query.data.fileUrl)} />
              )}
            </div>
            <Result analysis={query.data} />
            {query.data.evaluation && (
              <section className="panel">
                <h2>Перевірка на розміченому зразку</h2>
                <p>
                  Еталон: {query.data.evaluation.expectedLabel}. TOP-1:{" "}
                  {query.data.evaluation.top1Correct ? "збіг" : "не збігається"}
                  . TOP-3:{" "}
                  {query.data.evaluation.top3Correct ? "збіг" : "не збігається"}
                  .
                </p>
                <a
                  href={query.data.evaluation.labelSource}
                  target="_blank"
                  rel="noreferrer"
                >
                  Джерело еталонної мітки ↗
                </a>
              </section>
            )}
          </>
        )}
      </State>
    </>
  );
}

export function BirdDetails() {
  const { id } = useParams();
  const query = useApi<Bird>(`/birds/${id}`);
  return (
    <>
      <PageTitle
        eyebrow="ДОВІДНИК ВИДІВ"
        title={query.data?.ukrainianName || "Картка птаха"}
        text="Довідкова інформація з перевірених джерел початкового AI Bird Lab."
      />
      <State
        loading={query.isLoading}
        error={query.error}
        retry={() => void query.refetch()}
      >
        {query.data && <BirdInfo bird={query.data} />}
      </State>
    </>
  );
}
