import { NavigationContainer, DarkTheme } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { StatusBar } from "expo-status-bar";
import Home from "./src/screens/Home";
import { PhotoScreen, AudioScreen } from "./src/screens/Capture";
import History from "./src/screens/History";
import { AnalysisScreen, BirdScreen } from "./src/screens/Details";
import Statistics from "./src/screens/Statistics";
import Compare from "./src/screens/Compare";
import Info from "./src/screens/Info";
import type { Tabs, RootStack } from "./src/navigation";
import { colors } from "./src/theme";
import { AuthProvider, useAuth } from "./src/auth";
import MySubscriptionScreen, { LoginScreen } from "./src/screens/Account";

const Tab = createBottomTabNavigator<Tabs>();
const Stack = createNativeStackNavigator<RootStack>();
const icons = {
  Home: "leaf-outline",
  Photo: "camera-outline",
  Audio: "musical-notes-outline",
  History: "time-outline",
  Info: "person-circle-outline",
} as const;
function TabsScreen() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.green,
        tabBarInactiveTintColor: "#849580",
        tabBarStyle: {
          backgroundColor: "#111d15",
          borderTopColor: colors.border,
        },
        tabBarLabelStyle: { fontSize: 10, fontWeight: "600" },
        tabBarIcon: ({ color, size }) => (
          <Ionicons name={icons[route.name]} color={color} size={size} />
        ),
      })}
    >
      <Tab.Screen name="Home" component={Home} options={{ title: "Головна" }} />
      <Tab.Screen
        name="Photo"
        component={PhotoScreen}
        options={{ title: "Фото" }}
      />
      <Tab.Screen
        name="Audio"
        component={AudioScreen}
        options={{ title: "Аудіо" }}
      />
      <Tab.Screen
        name="History"
        component={History}
        options={{ title: "Історія" }}
      />
      <Tab.Screen
        name="Info"
        component={Info}
        options={{ title: "Інформація" }}
      />
    </Tab.Navigator>
  );
}
function GalleryScreen() {
  return <History gallery />;
}
function AuthenticatedApp() {
  const auth = useAuth();
  if (!auth.user) return <LoginScreen />;
  return (
    <>
      <StatusBar style="light" />
      <NavigationContainer
        theme={{
          ...DarkTheme,
          colors: {
            ...DarkTheme.colors,
            background: colors.background,
            card: colors.panel,
            text: colors.text,
            border: colors.border,
            primary: colors.green,
          },
        }}
      >
        <Stack.Navigator
          screenOptions={{
            headerTintColor: colors.green,
            headerStyle: { backgroundColor: colors.background },
            headerTitleStyle: { color: colors.text },
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <Stack.Screen
            name="Tabs"
            component={TabsScreen}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="Analysis"
            component={AnalysisScreen}
            options={{ title: "Спостереження" }}
          />
          <Stack.Screen
            name="Bird"
            component={BirdScreen}
            options={{ title: "Картка птаха" }}
          />
          <Stack.Screen
            name="Gallery"
            component={GalleryScreen}
            options={{ title: "Галерея" }}
          />
          <Stack.Screen
            name="Statistics"
            component={Statistics}
            options={{ title: "Статистика" }}
          />
          <Stack.Screen
            name="Subscription"
            component={MySubscriptionScreen}
            options={{ title: "Мій тариф" }}
          />
          <Stack.Screen
            name="Compare"
            component={Compare}
            options={{ title: "Порівняння" }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </>
  );
}
export default function App() { return <SafeAreaProvider><AuthProvider><AuthenticatedApp /></AuthProvider></SafeAreaProvider>; }
