import { useState } from "react";
import {
  Modal,
  Pressable,
  FlatList,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  birdFields,
  birdName,
  percent,
  type Bird,
  type Analysis,
  type Page,
  type BirdComparison,
  type ModelComparison,
} from "../../../shared/contracts";
import { useRemote } from "../api";
import { Button, Screen, State, Title } from "../components/Common";
import { colors, styles as s } from "../theme";

function Select({
  label,
  value,
  options,
  change,
}: {
  label: string;
  value: number | null;
  options: { id: number; label: string }[];
  change: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  return (
    <>
      <Text style={s.muted}>{label}</Text>
      <Button
        title={
          options.find((x) => x.id === value)?.label || "Оберіть зі списку"
        }
        icon="chevron-down"
        onPress={() => setOpen(true)}
      />
      <Modal
        visible={open}
        animationType="slide"
        onRequestClose={() => setOpen(false)}
      >
        <Screen scroll={false}>
          <View style={s.content}>
            <Button title="Закрити" onPress={() => setOpen(false)} />
            <TextInput
              style={s.input}
              placeholder="Пошук…"
              placeholderTextColor={colors.muted}
              value={search}
              onChangeText={setSearch}
            />
          </View>
          <FlatList
            data={options.filter((x) =>
              x.label.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
            )}
            keyExtractor={(x) => String(x.id)}
            renderItem={({ item }) => (
              <Pressable
                style={[s.card, { marginHorizontal: 20, marginBottom: 10 }]}
                onPress={() => {
                  change(item.id);
                  setOpen(false);
                  setSearch("");
                }}
              >
                <Text style={s.text}>{item.label}</Text>
              </Pressable>
            )}
            ListEmptyComponent={
              <Text style={[s.muted, { margin: 20 }]}>Нічого не знайдено.</Text>
            }
          />
        </Screen>
      </Modal>
    </>
  );
}

export default function CompareScreen() {
  const birds = useRemote<Bird[]>("/birds");
  const analyses = useRemote<Page<Analysis>>("/analyses?pageSize=100");
  const [first, setFirst] = useState<number | null>(null);
  const [second, setSecond] = useState<number | null>(null);
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);
  const comparison = useRemote<BirdComparison>(
    first && second && first !== second
      ? `/birds/compare?firstId=${first}&secondId=${second}`
      : null,
  );
  const models = useRemote<ModelComparison>(
    a && b && a !== b ? `/analyses/compare?firstId=${a}&secondId=${b}` : null,
  );
  const birdOptions =
    birds.data?.map((x) => ({
      id: x.id,
      label: `${x.ukrainianName || x.commonName} · ${x.scientificName}`,
    })) || [];
  const analysisOptions =
    analyses.data?.items.map((x) => ({
      id: x.id,
      label: `№${x.id} · ${x.analysisType === "image" ? "Фото" : "Аудіо"} · ${birdName(x)}`,
    })) || [];
  return (
    <Screen>
      <Title
        title="Порівняння"
        description="Характеристики видів та результати двох моделей зі спільної історії."
      />
      <State
        loading={
          (birds.loading && !birds.data) || (analyses.loading && !analyses.data)
        }
        error={birds.error || analyses.error}
        retry={() => {
          void birds.reload();
          void analyses.reload();
        }}
      >
        <View style={s.card}>
          <Text style={s.h2}>Два види</Text>
          <Select
            label="Перший вид"
            options={birdOptions}
            value={first}
            change={setFirst}
          />
          <Select
            label="Другий вид"
            options={birdOptions}
            value={second}
            change={setSecond}
          />
          {first && first === second ? (
            <Text style={s.error}>Оберіть різні види.</Text>
          ) : null}
          <State
            loading={
              comparison.loading && !!first && !!second && first !== second
            }
            error={comparison.error}
          >
            {comparison.data &&
              first !== second &&
              birdFields.map(([key, label]) => (
                <View key={key} style={s.divider}>
                  <Text style={s.link}>{label}</Text>
                  <Text style={s.muted}>
                    {comparison.data!.first.ukrainianName}
                  </Text>
                  <Text style={s.text}>
                    {String(comparison.data!.first[key] || "Немає даних")}
                  </Text>
                  <Text style={s.muted}>
                    {comparison.data!.second.ukrainianName}
                  </Text>
                  <Text style={s.text}>
                    {String(comparison.data!.second[key] || "Немає даних")}
                  </Text>
                </View>
              ))}
          </State>
        </View>
        <View style={s.card}>
          <Text style={s.h2}>Результати моделей</Text>
          <Text style={s.muted}>
            Оберіть два записи зі 100 останніх спостережень.
          </Text>
          <Select
            label="Перший аналіз"
            options={analysisOptions}
            value={a}
            change={setA}
          />
          <Select
            label="Другий аналіз"
            options={analysisOptions}
            value={b}
            change={setB}
          />
          {a && a === b ? (
            <Text style={s.error}>Оберіть різні аналізи.</Text>
          ) : null}
          <State
            loading={models.loading && !!a && !!b && a !== b}
            error={models.error}
          >
            {models.data && a !== b && (
              <>
                <Text style={s.link}>{models.data.conclusion}</Text>
                {[models.data.first, models.data.second].map((x) => (
                  <View key={x.id} style={s.divider}>
                    <Text style={s.h2}>
                      №{x.id} · {birdName(x)}
                    </Text>
                    <Text style={s.text}>
                      {x.bird?.scientificName || "Таксон не зіставлено"} ·{" "}
                      {percent(x.confidence)}
                    </Text>
                    <Text style={s.muted}>{x.modelName}</Text>
                  </View>
                ))}
              </>
            )}
          </State>
        </View>
      </State>
    </Screen>
  );
}
