export const SLM_BENCH_SETTINGS_STORAGE_KEY = 'slm_hust_bench_settings'

export const defaultSlmBenchSettings = {
  camera_ch1_index: 0,
  camera_ch2_index: 1,
  use_mock: false
}

export function readSlmBenchSettings() {
  const rawSettings = localStorage.getItem(SLM_BENCH_SETTINGS_STORAGE_KEY)
  return rawSettings
    ? { ...defaultSlmBenchSettings, ...JSON.parse(rawSettings) }
    : { ...defaultSlmBenchSettings }
}

export function writeSlmBenchSettings(settings) {
  localStorage.setItem(SLM_BENCH_SETTINGS_STORAGE_KEY, JSON.stringify({
    camera_ch1_index: settings.camera_ch1_index,
    camera_ch2_index: settings.camera_ch2_index,
    use_mock: settings.use_mock
  }))
}
