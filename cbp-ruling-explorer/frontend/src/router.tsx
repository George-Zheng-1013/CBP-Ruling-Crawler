import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { SearchPage } from './pages/SearchPage';
import { DetailPage } from './pages/DetailPage';
import { StatsPage } from './pages/StatsPage';
import { ClassifyPage } from './pages/ClassifyPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <SearchPage /> },
      { path: 'classify', element: <ClassifyPage /> },
      { path: 'ruling/:rulingNo', element: <DetailPage /> },
      { path: 'stats', element: <StatsPage /> },
    ],
  },
]);
