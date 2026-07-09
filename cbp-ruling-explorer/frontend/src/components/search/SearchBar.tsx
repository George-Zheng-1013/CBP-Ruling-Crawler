import { Box, Button, Paper, TextField } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { useState } from 'react';
import { useQueryStore } from '../../store/queryStore';

export function SearchBar() {
  const keyword = useQueryStore((s) => s.keyword);
  const rulingNo = useQueryStore((s) => s.rulingNo);
  const setKeyword = useQueryStore((s) => s.setKeyword);
  const setRulingNo = useQueryStore((s) => s.setRulingNo);

  const [kw, setKw] = useState(keyword);
  const [no, setNo] = useState(rulingNo);

  const submit = () => {
    setKeyword(kw.trim());
    setRulingNo(no.trim());
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }} elevation={1}>
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <TextField
          label="关键词"
          placeholder="匹配主题或全文描述"
          value={kw}
          onChange={(e) => setKw(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          size="small"
          sx={{ flex: 1, minWidth: 240 }}
        />
        <TextField
          label="裁定编号"
          placeholder="如 N12345"
          value={no}
          onChange={(e) => setNo(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          size="small"
          sx={{ width: 200 }}
        />
        <Button variant="contained" startIcon={<SearchIcon />} onClick={submit}>
          搜索
        </Button>
      </Box>
    </Paper>
  );
}
