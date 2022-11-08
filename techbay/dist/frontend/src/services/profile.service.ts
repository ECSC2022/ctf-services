import { profileApi } from '@/api';
import type { ProfileInfo, ProfileInfoCurrentUser } from '@/api/generated';

export async function getProfileOfCurrentUser(): Promise<ProfileInfoCurrentUser> {
  return profileApi().getProfile();
}

export async function getProfile(userId: number): Promise<ProfileInfo> {
  return profileApi().getProfileByUserId(userId);
}

export async function updateProfile(profileInfo: ProfileInfoCurrentUser): Promise<void> {
  await profileApi().updateProfile(profileInfo);
}
