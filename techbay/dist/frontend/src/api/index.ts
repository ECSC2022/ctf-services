import {
  AuthenticationApi,
  AuthenticationApiFactory,
  Configuration,
  type FetchAPI,
  ProfileApi,
  ProfileApiFactory,
  RequestApi,
  RequestApiFactory,
  TradingApi,
  TradingApiFactory,
} from '@/api/generated';
import { userStore } from '@/stores/user-store';

type ApiType = AuthenticationApi & ProfileApi & RequestApi & TradingApi;

function constructApi(
  factory: (
    configuration: Configuration | undefined,
    fetch: FetchAPI,
    basePath: string | undefined,
  ) => any,
): ApiType {
  const configuration = new Configuration({ apiKey: `Bearer ${userStore.token}` });
  return factory(userStore.token ? configuration : undefined, fetch, '');
}

export function authenticationApi(): AuthenticationApi {
  return constructApi(AuthenticationApiFactory);
}

export function profileApi(): ProfileApi {
  return constructApi(ProfileApiFactory);
}

export function requestApi(): RequestApi {
  return constructApi(RequestApiFactory);
}

export function tradingApi(): TradingApi {
  return constructApi(TradingApiFactory);
}
