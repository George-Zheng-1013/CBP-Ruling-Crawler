import { Box, Grid, Paper, Typography } from '@mui/material';
import { StatsOverviewFE } from '../../types/ruling';
import { YearBarChart } from './YearBarChart';
import { StatusPieChart } from './StatusPieChart';

interface Props {
  stats: StatsOverviewFE;
}

export function StatsOverview({ stats }: Props) {
  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }} elevation={1}>
            <Typography variant="h4" color="primary.main" fontWeight={700}>
              {stats.total}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              裁定总数
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }} elevation={1}>
            <Typography variant="h4" color="error.main" fontWeight={700}>
              {stats.parseFailed}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              解析失败数
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }} elevation={1}>
            <Typography variant="h4" fontWeight={700}>
              {stats.byYear.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              覆盖年份
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }} elevation={1}>
            <Typography variant="h4" fontWeight={700}>
              {stats.byStatus.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              状态种类
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 2 }} elevation={1}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              按年份分布
            </Typography>
            <YearBarChart data={stats.byYear} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2 }} elevation={1}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              按状态分布
            </Typography>
            <StatusPieChart data={stats.byStatus} />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
