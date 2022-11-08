import { authenticationApi } from '@/api';
import type { UserInfo } from '@/api/generated';
import { sha3_512 } from 'js-sha3';

export async function login(username: string, password: string): Promise<UserInfo> {
  const hashedPassword = sha3_512(password);
  return authenticationApi().login({ username, hashedPassword });
}

export async function register(
  username: string,
  password: string,
  passport: string,
): Promise<void> {
  const hashedPassword = sha3_512(password);
  await authenticationApi().register({
    username: username,
    hashedPassword: hashedPassword,
    passport,
  });
}

export async function getCurrentUser(): Promise<UserInfo> {
  return authenticationApi().getCurrentUser();
}
