import { tradingApi } from '@/api';
import type { Offer } from '@/api/generated';

export async function addOffer(name: string, description: string, image: string): Promise<void> {
  await tradingApi().addOffer({ name, description, picture: image });
}

export async function getOffer(offerId: number): Promise<Offer> {
  return tradingApi().getOffer(offerId);
}

export async function deleteOffer(offerId: number): Promise<void> {
  await tradingApi().deleteOffer(offerId);
}

export async function getMyOffers(
  page: number,
  nameOrder: 'asc' | 'desc' | undefined,
  creationOrder: 'asc' | 'desc' | undefined,
  limit: number,
): Promise<Offer[]> {
  return await tradingApi().getMyOffers(page, nameOrder, creationOrder, limit);
}

export async function getOffers(
  page: number,
  nameOrder: 'asc' | 'desc' | undefined,
  creationOrder: 'asc' | 'desc' | undefined,
  limit: number,
): Promise<Offer[]> {
  return tradingApi().getOffers(page, nameOrder, creationOrder, limit);
}
