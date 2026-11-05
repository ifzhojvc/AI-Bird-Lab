import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useApi } from "../api";
import { PageTitle, State } from "../components/Common";
import type { Entitlement } from "../../../shared/subscriptions";
import {
  percent,
  type Summary,
  type SpeciesCount,
  type ConfidenceBin,
  type EvaluationStats,
} from "../../../shared/contracts";

export default function Statistics() {
  const access = useApi<Entitlement>("/subscriptions/me");
  const summary = useApi<Summary>("/statistics/summary");
  const species = useApi<SpeciesCount[]>("/statistics/species");
  const bins = useApi<ConfidenceBin[]>("/statistics/confidence");
  const evaluations = useApi<EvaluationStats[]>("/statistics/evaluations", !!access.data?.features.includes("advancedStatistics"));
  const error =
    summary.error || species.error || bins.error || evaluations.error;
  return (
    <>
      <PageTitle
        eyebrow="ДАНІ ВАШОЇ ЛАБОРАТОРІЇ"
        title="Статистика спостережень"
        text="Живі показники спільної бази. Confidence та точність на еталонах показані окремо."
      />
      <State
        loading={
          summary.isLoading ||
          species.isLoading ||
          bins.isLoading ||
          evaluations.isLoading
        }
        error={error}
        empty={summary.data?.totalAnalyses === 0}
        retry={() => {
          void summary.refetch();
          void species.refetch();
          void bins.refetch();
          void evaluations.refetch();
        }}
      >
        <div className="stat-grid">
          {[
            ["Фотоаналізи", summary.data?.imageAnalyses],
            ["Аудіоаналізи", summary.data?.audioAnalyses],
            ["Мін. confidence", percent(summary.data?.minConfidence)],
            ["Макс. confidence", percent(summary.data?.maxConfidence)],
          ].map(([name, value]) => (
            <div className="panel stat" key={name}>
              <span>{name}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        <div className="chart-grid">
          <section className="panel">
            <h2>Найчастіші передбачення</h2>
            <p className="caption">Кількість результатів за класом моделі</p>
            <div className="chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={species.data?.slice(0, 10)}
                  layout="vertical"
                  margin={{ left: 10, right: 25 }}
                >
                  <CartesianGrid stroke="#26332c" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} stroke="#8b9c91" />
                  <YAxis
                    type="category"
                    dataKey="species"
                    width={115}
                    stroke="#8b9c91"
                    tick={{ fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#142119",
                      border: "1px solid #304a39",
                      borderRadius: 10,
                    }}
                    labelStyle={{ color: "#eaf1e8" }}
                  />
                  <Bar
                    dataKey="count"
                    name="Аналізів"
                    fill="#bcdf69"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="panel">
            <h2>Розподіл confidence</h2>
            <p className="caption">Впевненість TOP-1 для всіх аналізів</p>
            <div className="chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bins.data}>
                  <CartesianGrid stroke="#26332c" vertical={false} />
                  <XAxis dataKey="label" stroke="#8b9c91" />
                  <YAxis allowDecimals={false} stroke="#8b9c91" />
                  <Tooltip
                    contentStyle={{
                      background: "#142119",
                      border: "1px solid #304a39",
                    }}
                  />
                  <Bar
                    dataKey="count"
                    name="Аналізів"
                    fill="#5eaa80"
                    radius={[5, 5, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>
        <section className="panel">
          <h2>Оцінювання на розмічених зразках</h2>
          <p>
            Ці результати стосуються лише вказаних еталонних фотографій. Вони не
            визначають загальну точність моделі.
          </p>
          {evaluations.data?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Модель / дослід</th>
                    <th>Зразків</th>
                    <th>TOP-1 збігів</th>
                    <th>TOP-3 збігів</th>
                  </tr>
                </thead>
                <tbody>
                  {evaluations.data.map((e) => (
                    <tr key={`${e.model}-${e.experiment}`}>
                      <td>
                        {e.model}
                        <small>{e.experiment}</small>
                      </td>
                      <td>{e.samples}</td>
                      <td>
                        {e.top1Correct} / {e.samples}
                      </td>
                      <td>
                        {e.top3Correct} / {e.samples}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="notice">
              Ще немає аналізів із перевіреними еталонними мітками.
            </p>
          )}
        </section>
      </State>
    </>
  );
}
