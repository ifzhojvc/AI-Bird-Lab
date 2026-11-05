import { useState } from "react";
import { FlatList, Text, TextInput, View } from "react-native";
import {
  AnalysisCard,
  Button,
  Screen,
  State,
  Title,
} from "../components/Common";
import { useRemote } from "../api";
import { colors, styles as s } from "../theme";
import type { Analysis, Page } from "../../../shared/contracts";

export default function HistoryScreen({
  gallery = false,
}: {
  gallery?: boolean;
}) {
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [sort, setSort] = useState("date_desc");
  const [page, setPage] = useState(1);
  const query = useRemote<Page<Analysis>>(
    `/analyses${gallery ? "/gallery" : ""}?page=${page}&pageSize=15&search=${encodeURIComponent(search)}&analysisType=${gallery ? "image" : kind}&sort=${sort}`,
  );
  const header = (
    <View style={s.content}>
      <Title
        title={gallery ? "Галерея птахів" : "Моя історія"}
        description="Спостереження з усіх пристроїв. Потягніть список униз, щоб оновити."
      />
      <TextInput
        accessibilityLabel="Пошук у спільній історії"
        style={s.input}
        placeholder="Вид або назва файлу…"
        placeholderTextColor={colors.muted}
        value={search}
        onChangeText={(text) => {
          setSearch(text);
          setPage(1);
        }}
        clearButtonMode="while-editing"
      />
      {!gallery && (
        <View style={s.wrap}>
          {[
            ["", "Усі"],
            ["image", "Фото"],
            ["audio", "Аудіо"],
          ].map(([value, label]) => (
            <Button
              key={value}
              primary={kind === value}
              title={label}
              onPress={() => {
                setKind(value);
                setPage(1);
              }}
            />
          ))}
        </View>
      )}
      <View style={s.wrap}>
        <Button
          title={
            sort === "date_desc"
              ? "Нові → старі"
              : sort === "date_asc"
                ? "Старі → нові"
                : "За confidence"
          }
          icon="swap-vertical-outline"
          onPress={() => {
            setSort(
              sort === "date_desc"
                ? "date_asc"
                : sort === "date_asc"
                  ? "confidence_desc"
                  : "date_desc",
            );
            setPage(1);
          }}
        />
        <Button
          title="Оновити"
          icon="refresh-outline"
          onPress={() => void query.reload()}
        />
      </View>
      {query.data && (
        <Text style={s.muted}>
          Знайдено: {query.data.total} · Сторінка {page}
        </Text>
      )}
      <State
        loading={query.loading && !query.data}
        error={query.error}
        empty={query.data?.total === 0}
        retry={() => void query.reload()}
      />
    </View>
  );
  return (
    <Screen scroll={false}>
      <FlatList
        data={query.error ? [] : query.data?.items || []}
        keyExtractor={(a) => String(a.id)}
        ListHeaderComponent={header}
        renderItem={({ item }) => (
          <AnalysisCard analysis={item} gallery={gallery} />
        )}
        refreshing={query.loading}
        onRefresh={() => void query.reload()}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ paddingBottom: 25 }}
        ListFooterComponent={
          query.data && query.data.total > 0 && !query.error ? (
            <View
              style={[s.row, { margin: 20, justifyContent: "space-between" }]}
            >
              <Button
                title="Назад"
                disabled={page === 1}
                onPress={() => setPage((p) => p - 1)}
              />
              <Button
                title="Далі"
                disabled={page * 15 >= query.data.total}
                onPress={() => setPage((p) => p + 1)}
              />
            </View>
          ) : null
        }
      />
    </Screen>
  );
}
