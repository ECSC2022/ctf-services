import { requestApi } from '@/api';
import type { Request } from '@/api/generated';

export async function getRequestsByOthers(): Promise<Request[]> {
  return requestApi().getRequestsByOthers();
}

export async function getRequestsByMe(): Promise<Request[]> {
  return requestApi().getRequestsByMe();
}

export async function requestOffer(offerId: number): Promise<void> {
  await requestApi().requestOffer(offerId);
}

export async function acceptRequest(id: number): Promise<void> {
  await requestApi().acceptRequest(id);
}

export async function takebackRequest(id: number): Promise<void> {
  await requestApi().takebackRequest(id);
}

export async function denyRequest(id: number): Promise<void> {
  await requestApi().denyRequest(id);
}
