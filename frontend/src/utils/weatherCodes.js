import { Sun, CloudSun, Cloud, CloudFog, CloudDrizzle, CloudRain, CloudSnow, CloudLightning, Moon, CloudMoon } from 'lucide-react'

// Centralized WMO weather_code -> icon mapping (per weather_service.py's
// own comment: "do not duplicate this mapping across components" -- this
// is the ONE place in the frontend that owns it). The backend never sends
// icon names, only the raw WMO code + a resolved `condition` string, so
// backend and frontend can't drift out of sync on icon choice.
// `isDay` (optional, default true) only changes the clear/mainly-clear icons
// to a moon at night; every other code looks the same day or night.
export function iconForWeatherCode(code, isDay = true) {
  if (code === 0) return isDay === false ? Moon : Sun
  if (code === 1) return isDay === false ? CloudMoon : CloudSun
  if (code === 2 || code === 3) return Cloud
  if (code === 45 || code === 48) return CloudFog
  if ([51, 53, 55, 56, 57].includes(code)) return CloudDrizzle
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return CloudRain
  if ([71, 73, 75, 77, 85, 86].includes(code)) return CloudSnow
  if ([95, 96, 99].includes(code)) return CloudLightning
  return Cloud
}

/**
 * WMO condition label keys. Keep weather wording in the locale dictionaries,
 * not in provider-supplied English strings.
 */
export function weatherConditionKey(code) {
  if (code === 0) return 'weatherPage.condition.clear'
  if (code === 1) return 'weatherPage.condition.mainlyClear'
  if (code === 2) return 'weatherPage.condition.partlyCloudy'
  if (code === 3) return 'weatherPage.condition.overcast'
  if ([45, 48].includes(code)) return 'weatherPage.condition.fog'
  if ([51, 53, 55].includes(code)) return 'weatherPage.condition.drizzle'
  if ([56, 57].includes(code)) return 'weatherPage.condition.freezingDrizzle'
  if ([61, 63, 65].includes(code)) return 'weatherPage.condition.rain'
  if ([66, 67].includes(code)) return 'weatherPage.condition.freezingRain'
  if ([71, 73, 75, 77].includes(code)) return 'weatherPage.condition.snow'
  if ([80, 81, 82].includes(code)) return 'weatherPage.condition.showers'
  if ([85, 86].includes(code)) return 'weatherPage.condition.snowShowers'
  if ([95, 96, 99].includes(code)) return 'weatherPage.condition.thunderstorm'
  return 'weatherPage.condition.unknown'
}
