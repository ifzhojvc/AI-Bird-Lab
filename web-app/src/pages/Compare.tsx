import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, useApi } from "../api";
import { PageTitle, State } from "../components/Common";
import {
  birdFields,
  birdName,
  percent,
  type Analysis,
  type Bird,
  type BirdComparison,
  type ModelComparison,
  type Page,
} from "../../../shared/contracts";

export default function Compare() {
  const birds = useApi<Bird[]>("/birds");
  const analyses = useApi<Page<Analysis>>("/analyses?pageSize=100");
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const comparison = useQuery({
    queryKey: ["compare", first, second],
    enabled: !!first && !!second && first !== second,
    queryFn: () =>
      api.request<BirdComparison>(
        `/birds/compare?firstId=${first}&secondId=${second}`,
      ),
  });
  const models = useQuery({
    queryKey: ["model-compare", a, b],
    enabled: !!a && !!b && a !== b,
    queryFn: () =>
      api.request<ModelComparison>(
        `/analyses/compare?firstId=${a}&secondId=${b}`,
      ),
  });
  const selectBird = (
    label: string,
    value: string,
    change: (v: string) => void,
  ) => (
    <label>
      {label}
      <select
        aria-label={label}
        value={value}
        onChange={(e) => change(e.target.value)}
      >
        <option value="">Оберіть вид</option>
        {birds.data?.map((x) => (
          <option key={x.id} value={x.id}>
            {x.ukrainianName || x.commonName} · {x.scientificName}
          </option>
        ))}
      </select>
    </label>
  );
  const selectAnalysis = (
    label: string,
    value: string,
    change: (v: string) => void,
  ) => (
    <label>
      {label}
      <select
        aria-label={label}
        value={value}
        onChange={(e) => change(e.target.value)}
      >
        <option value="">Оберіть аналіз</option>
        {analyses.data?.items.map((x) => (
          <option key={x.id} value={x.id}>
            №{x.id} · {x.analysisType === "image" ? "Фото" : "Аудіо"} ·{" "}
            {birdName(x)}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <>
      <PageTitle
        eyebrow="ДОСЛІДЖУЙТЕ ВІДМІННОСТІ"
        title="Порівняння видів і моделей"
        text="Зіставте характеристики птахів або два збережені результати фото- та аудіомоделей."
      />
      <State
        loading={birds.isLoading || analyses.isLoading}
        error={birds.error || analyses.error}
        retry={() => {
          void birds.refetch();
          void analyses.refetch();
        }}
      >
        <section className="panel">
          <h2>Характеристики двох видів</h2>
          <div className="compare-selects">
            {selectBird("Перший вид", first, setFirst)}
            {selectBird("Другий вид", second, setSecond)}
          </div>
          {first && first === second && (
            <p role="alert">Оберіть два різні види.</p>
          )}
          <State loading={comparison.isFetching} error={comparison.error}>
            {comparison.data && first !== second && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Характеристика</th>
                      <th>{comparison.data.first.ukrainianName}</th>
                      <th>{comparison.data.second.ukrainianName}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {birdFields.map(([field, label]) => (
                      <tr key={field}>
                        <th>{label}</th>
                        <td>
                          {String(
                            comparison.data.first[field] || "Немає даних",
                          )}
                        </td>
                        <td>
                          {String(
                            comparison.data.second[field] || "Немає даних",
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </State>
        </section>
        <section className="panel">
          <h2>Результати моделей</h2>
          <p>
            Виберіть два спостереження зі 100 останніх записів. Можна порівняти
            фото з аудіо.
          </p>
          <div className="compare-selects">
            {selectAnalysis("Перший результат", a, setA)}
            {selectAnalysis("Другий результат", b, setB)}
          </div>
          {a && a === b && <p role="alert">Оберіть два різні аналізи.</p>}
          <State loading={models.isFetching} error={models.error}>
            {models.data && a !== b && (
              <>
                <p className="notice">{models.data.conclusion}</p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Показник</th>
                        <th>№{models.data.first.id}</th>
                        <th>№{models.data.second.id}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ["Модель", "modelName"],
                        ["Передбачення", "predictedSpecies"],
                      ].map(([label, field]) => (
                        <tr key={field}>
                          <th>{label}</th>
                          <td>
                            {String(models.data.first[field as keyof Analysis])}
                          </td>
                          <td>
                            {String(
                              models.data.second[field as keyof Analysis],
                            )}
                          </td>
                        </tr>
                      ))}
                      <tr>
                        <th>Наукова назва</th>
                        <td>
                          {models.data.first.bird?.scientificName ||
                            "Не зіставлено"}
                        </td>
                        <td>
                          {models.data.second.bird?.scientificName ||
                            "Не зіставлено"}
                        </td>
                      </tr>
                      <tr>
                        <th>Confidence</th>
                        <td>{percent(models.data.first.confidence)}</td>
                        <td>{percent(models.data.second.confidence)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </State>
        </section>
      </State>
    </>
  );
}
