import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FavoritesStore {
  favorites: string[];
  toggle: (rulingNo: string) => void;
  has: (rulingNo: string) => boolean;
  clear: () => void;
}

// 收藏仅存于前端 localStorage（key: cbp_favorites），不写后端。
export const useFavorites = create<FavoritesStore>()(
  persist(
    (set, get) => ({
      favorites: [],
      toggle: (rulingNo) =>
        set((s) => ({
          favorites: s.favorites.includes(rulingNo)
            ? s.favorites.filter((x) => x !== rulingNo)
            : [...s.favorites, rulingNo],
        })),
      has: (rulingNo) => get().favorites.includes(rulingNo),
      clear: () => set({ favorites: [] }),
    }),
    { name: 'cbp_favorites' },
  ),
);
