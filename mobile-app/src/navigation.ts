import type { NavigatorScreenParams } from "@react-navigation/native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

export type Tabs = {
  Home: undefined;
  Photo: undefined;
  Audio: undefined;
  History: undefined;
  Info: undefined;
};
export type RootStack = {
  Tabs: NavigatorScreenParams<Tabs> | undefined;
  Analysis: { id: number };
  Bird: { id: number };
  Gallery: undefined;
  Statistics: undefined;
  Compare: undefined;
  Subscription: undefined;
};
export const useLabNavigation = () =>
  useNavigation<NativeStackNavigationProp<RootStack>>();
