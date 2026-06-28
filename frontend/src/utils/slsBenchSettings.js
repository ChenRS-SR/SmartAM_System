export const SLS_BENCH_SETTINGS_STORAGE_KEY = 'sls_bench_settings'

export const defaultSlsBenchSettings = {
  fotric_ip: '192.168.1.100',
  vibration_com: 'COM5',
  servo_com: 'COM6',
  vibration_threshold: 0.1,
  vibration_algorithm: 'composite',
  use_mock: false
}

export function readSlsBenchSettings() {
  const rawSettings = localStorage.getItem(SLS_BENCH_SETTINGS_STORAGE_KEY)
  return rawSettings
    ? { ...defaultSlsBenchSettings, ...JSON.parse(rawSettings) }
    : { ...defaultSlsBenchSettings }
}

export function writeSlsBenchSettings(settings) {
  localStorage.setItem(SLS_BENCH_SETTINGS_STORAGE_KEY, JSON.stringify({
    fotric_ip: settings.fotric_ip,
    vibration_com: settings.vibration_com,
    servo_com: settings.servo_com,
    vibration_threshold: Number(settings.vibration_threshold),
    vibration_algorithm: settings.vibration_algorithm,
    use_mock: Boolean(settings.use_mock)
  }))
}
