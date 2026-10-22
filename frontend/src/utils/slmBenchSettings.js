export const SLM_BENCH_SETTINGS_STORAGE_KEY = 'slm_hust_bench_settings'

export const defaultSlmBenchSettings = {
  camera_ch1_index: 0,
  camera_ch2_index: 4,
  vibration_com: 'COM3',
  vibration_threshold: 0.05,
  save_directory: '',
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
    vibration_com: settings.vibration_com,
    vibration_threshold: settings.vibration_threshold,
    save_directory: settings.save_directory,
    use_mock: settings.use_mock
  }))
}
