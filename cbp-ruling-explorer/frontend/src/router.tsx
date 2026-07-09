import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { SearchPage } from './pages/SearchPage';
import { DetailPage } from './pages/DetailPage';
import { StatsPage } from './pages/StatsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <SearchPage /> },
      { path: 'ruling/:rulingNo', element: <DetailPage /> },
      { path: 'stats', element: <StatsPage /> },
    ],
  },
]);
