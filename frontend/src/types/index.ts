// ── Uploads ──────────────────────────────────────────────────────────────────

export interface DatasetOut {
  dataset_id: string
  filename: string
  upload_ts: string
  row_count: number
  channels: string[]
  date_min: string
  date_max: string
  is_hourly: boolean
  has_aht: boolean
  project_id: string | null
  is_actuals: boolean
}

export interface Project {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
}

export interface PasskeyOut {
  id: string
  name: string
  created_at: string
}

export interface DatasetSummary {
  dataset_id: string
  filename: string
  upload_ts: string
  row_count: number
  is_active: boolean
}

// ── Channels ─────────────────────────────────────────────────────────────────

export interface ChannelInfo {
  name: string
  row_count: number
  date_min: string
  date_max: string
  is_hourly: boolean
  has_aht: boolean
}

export interface HourlyPoint {
  hour: number        // 0–23
  avg_volume: number
}

export interface ObservationPoint {
  date: string
  volume: number
  is_actuals?: boolean
}

export interface MonthlyObservation {
  month: string
  total: number
}

// ── Training ─────────────────────────────────────────────────────────────────

export interface TrainingRequest {
  dataset_id: string
  channels: string[]
  months_ahead: number
}

export interface ChannelTrainingResult {
  channel: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  config: [string, string, boolean] | null
  aic: number | null
  backtest_mape: number | null
  message: string | null
  started_at: string | null
  completed_at: string | null
}

export interface TrainingJobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  results: ChannelTrainingResult[]
}

// ── Forecasts ─────────────────────────────────────────────────────────────────

export interface ForecastPoint {
  date: string
  yhat: number
  yhat_lower: number
  yhat_upper: number
  aht_yhat: number | null
}

// ── Hiring Waves ──────────────────────────────────────────────────────────────

export interface HiringWave {
  id: string
  channel: string
  start_date: string
  end_date: string
  junior_count: number
  total_agents: number
  junior_ratio: number
  label: string | null
  created_at: string
}

export interface HiringWaveCreate {
  channel: string
  start_date: string
  end_date: string
  junior_count: number
  total_agents: number
  label?: string
}

export interface ModelInfo {
  config: [string, string, boolean] | null
  aic: number | null
  backtest_mape: number | null
  backtest_mae: number | null
  monthly_factors: Record<string, number> | null
}

export interface ForecastResponse {
  channel: string
  model: ModelInfo
  data: ForecastPoint[]
}

export interface MonthlyPoint {
  month: string
  total: number
}

export interface MonthlyForecastPoint {
  month: string
  total: number
  lower: number
  upper: number
}

export interface MonthlyForecastResponse {
  channel: string
  historical: MonthlyPoint[]
  forecast: MonthlyForecastPoint[]
}

export interface BacktestPoint {
  date: string
  actual: number
  predicted: number
  error_pct: number | null
}

export interface BacktestMetrics {
  mape: number
  mae: number
  rmse: number
  holdout_days: number
}

export interface BacktestResponse {
  channel: string
  metrics: BacktestMetrics
  data: BacktestPoint[]
}

export interface SeasonalityResponse {
  channel: string
  monthly_factors: Record<string, number>
  weekly_pattern: Array<{ day: string; effect: number }>
}

// ── Config ───────────────────────────────────────────────────────────────────

export interface HolidayConfigRequest {
  channel: string
  country_code: string
}

export interface MonthlyTargetsRequest {
  channel: string
  targets: Record<string, number>
}

export interface ConfigResponse {
  holidays: Record<string, string>
  targets: Record<string, Record<string, number>>
}

// ── Summary ───────────────────────────────────────────────────────────────────

export interface SummaryRow {
  channel: string
  hist_avg_daily: number
  forecast_avg_daily: number
  change_pct: number
  total_15m: number
  peak_month: string
  trough_month: string
  has_holidays: boolean
  has_targets: boolean
}
