import { Button, Menu, MenuItem } from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { useState } from 'react';
import { buildExportUrl } from '../../api/rulings';
import { useQueryStore } from '../../store/queryStore';
import { ExportFormat } from '../../types/ruling';

export function ExportButton() {
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const { keyword, rulingNo, year, status, hsCode } = useQueryStore();

  const handleExport = (format: ExportFormat) => {
    setAnchor(null);
    const url = buildExportUrl(
      {
        keyword,
        rulingNo,
        year: year ?? undefined,
        status,
        hsCode,
        pageSize: 25,
        sort: 'year_desc',
      },
      format,
    );
    window.open(url, '_blank');
  };

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<FileDownloadIcon />}
        onClick={(e) => setAnchor(e.currentTarget)}
      >
        导出
      </Button>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
      >
        <MenuItem onClick={() => handleExport('csv')}>导出 CSV</MenuItem>
        <MenuItem onClick={() => handleExport('json')}>导出 JSON</MenuItem>
      </Menu>
    </>
  );
}
