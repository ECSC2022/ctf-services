import { reactive } from 'vue';
import type { UserInfo } from '@/api/generated';

interface UserStoreData {
  user: UserInfo | undefined;
  isLoggedIn: boolean;
  token: string | undefined;
}

export const userStore = reactive<UserStoreData>({
  user: undefined,
  isLoggedIn: false,
  token: undefined,
});
