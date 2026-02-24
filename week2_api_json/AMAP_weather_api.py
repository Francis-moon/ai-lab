from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
AMAP_DISTRICT_URL = "https://restapi.amap.com/v3/config/district"
DEFAULT_TIMEOUT = 10


class AMapWeatherAPIError(RuntimeError):
    """高德天气接口调用异常。"""


def _get_amap_key() -> str:
    """
    从环境变量读取高德 Web 服务 Key。
    兼容常见变量名：
    - AMAP_WEATHER_KEY
    - AMAP_API_KEY
    - AMAP_whether_key（历史拼写）
    """
    key = (
        os.getenv("AMAP_WEATHER_KEY", "").strip()
        or os.getenv("AMAP_API_KEY", "").strip()
        or os.getenv("AMAP_whether_key", "").strip()
    )
    if not key:
        raise AMapWeatherAPIError(
            "未找到高德 API Key，请在 .env 或环境变量中设置 "
            "`AMAP_WEATHER_KEY`（或 `AMAP_whether_key`）。"
        )
    return key


def _request_weather(city_adcode: str, extensions: str, *, retries: int = 3) -> Dict[str, Any]:
    """
    调用高德天气接口。

    参数：
    - city_adcode: 城市 adcode（如北京 110000）
    - extensions: 'base'（实时天气）或 'all'（天气预报）
    """
    if extensions not in {"base", "all"}:
        raise ValueError("extensions 只能是 'base' 或 'all'")

    params = {
        "key": _get_amap_key(),
        "city": city_adcode,
        "extensions": extensions,
        "output": "JSON",
    }

    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.get(AMAP_WEATHER_URL, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
            if data.get("status") != "1":
                raise AMapWeatherAPIError(
                    f"高德天气接口返回失败: info={data.get('info')} "
                    f"infocode={data.get('infocode')}"
                )
            return data
        except (requests.RequestException, ValueError, AMapWeatherAPIError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(attempt + 1)
                continue
            raise AMapWeatherAPIError(
                f"请求高德天气接口失败（city={city_adcode}, extensions={extensions}）: {e}"
            ) from e

    raise AMapWeatherAPIError(f"请求高德天气接口失败: {last_err}")


def _request_district(keywords: str, *, retries: int = 3) -> Dict[str, Any]:
    """
    调用高德行政区查询接口，将中文城市名解析为 adcode。
    """
    params = {
        "key": _get_amap_key(),
        "keywords": keywords,
        "subdistrict": 0,
        "extensions": "base",
        "output": "JSON",
    }

    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.get(AMAP_DISTRICT_URL, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
            if data.get("status") != "1":
                raise AMapWeatherAPIError(
                    f"高德行政区接口返回失败: info={data.get('info')} "
                    f"infocode={data.get('infocode')}"
                )
            return data
        except (requests.RequestException, ValueError, AMapWeatherAPIError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(attempt + 1)
                continue
            raise AMapWeatherAPIError(f"请求高德行政区接口失败（keywords={keywords}）: {e}") from e

    raise AMapWeatherAPIError(f"请求高德行政区接口失败: {last_err}")


def resolve_city_to_adcode(city_or_adcode: str) -> str:
    """
    将输入解析为 adcode：
    - 纯数字（如 110000）直接返回
    - 中文城市名（如 北京 / 北京市）调用行政区接口解析
    """
    city_or_adcode = city_or_adcode.strip()
    if not city_or_adcode:
        raise AMapWeatherAPIError("城市名称不能为空")

    if city_or_adcode.isdigit():
        return city_or_adcode

    data = _request_district(city_or_adcode)
    districts = data.get("districts") or []
    if not districts:
        raise AMapWeatherAPIError(f"未找到城市对应的 adcode：{city_or_adcode}")

    adcode = str(districts[0].get("adcode", "")).strip()
    if not adcode:
        raise AMapWeatherAPIError(f"城市解析成功但未返回 adcode：{city_or_adcode}")
    return adcode


@dataclass
class LiveWeather:
    province: str
    city: str
    adcode: str
    weather: str
    temperature: str
    winddirection: str
    windpower: str
    humidity: str
    reporttime: str


@dataclass
class ForecastCast:
    date: str
    week: str
    dayweather: str
    nightweather: str
    daytemp: str
    nighttemp: str
    daywind: str
    nightwind: str
    daypower: str
    nightpower: str


@dataclass
class WeatherForecast:
    city: str
    adcode: str
    province: str
    reporttime: str
    casts: List[ForecastCast]


def get_live_weather(city_adcode: str) -> LiveWeather:
    """获取实时天气（extensions=base）。参数应为 adcode。"""
    data = _request_weather(city_adcode, "base")
    lives = data.get("lives") or []
    if not lives:
        raise AMapWeatherAPIError(f"未获取到实时天气数据，city={city_adcode}")

    item = lives[0]
    return LiveWeather(
        province=str(item.get("province", "")),
        city=str(item.get("city", "")),
        adcode=str(item.get("adcode", "")),
        weather=str(item.get("weather", "")),
        temperature=str(item.get("temperature", "")),
        winddirection=str(item.get("winddirection", "")),
        windpower=str(item.get("windpower", "")),
        humidity=str(item.get("humidity", "")),
        reporttime=str(item.get("reporttime", "")),
    )


def get_forecast_weather(city_adcode: str) -> WeatherForecast:
    """获取未来天气预报（extensions=all）。参数应为 adcode。"""
    data = _request_weather(city_adcode, "all")
    forecasts = data.get("forecasts") or []
    if not forecasts:
        raise AMapWeatherAPIError(f"未获取到天气预报数据，city={city_adcode}")

    fc = forecasts[0]
    casts: List[ForecastCast] = []
    for c in fc.get("casts", []) or []:
        casts.append(
            ForecastCast(
                date=str(c.get("date", "")),
                week=str(c.get("week", "")),
                dayweather=str(c.get("dayweather", "")),
                nightweather=str(c.get("nightweather", "")),
                daytemp=str(c.get("daytemp", "")),
                nighttemp=str(c.get("nighttemp", "")),
                daywind=str(c.get("daywind", "")),
                nightwind=str(c.get("nightwind", "")),
                daypower=str(c.get("daypower", "")),
                nightpower=str(c.get("nightpower", "")),
            )
        )

    return WeatherForecast(
        city=str(fc.get("city", "")),
        adcode=str(fc.get("adcode", "")),
        province=str(fc.get("province", "")),
        reporttime=str(fc.get("reporttime", "")),
        casts=casts,
    )


def get_weather(city: str) -> Dict[str, Any]:
    """
    获取某城市（adcode 或中文城市名）的实时天气 + 未来预报。
    """
    adcode = resolve_city_to_adcode(city)
    live = get_live_weather(adcode)
    forecast = get_forecast_weather(adcode)
    return {
        "live": live.__dict__,
        "forecast": {
            "city": forecast.city,
            "adcode": forecast.adcode,
            "province": forecast.province,
            "reporttime": forecast.reporttime,
            "casts": [c.__dict__ for c in forecast.casts],
        },
    }


def get_weather_by_city_name(city_name: str) -> Dict[str, Any]:
    """根据中文城市名（如“北京”）获取实时天气 + 未来预报。"""
    return get_weather(city_name)


_KEY_ZH_MAP = {
    "live": "实时天气",
    "forecast": "天气预报",
    "province": "省份",
    "city": "城市",
    "adcode": "城市编码",
    "weather": "天气",
    "temperature": "气温",
    "winddirection": "风向",
    "windpower": "风力",
    "humidity": "湿度",
    "reporttime": "发布时间",
    "casts": "预报列表",
    "date": "日期",
    "week": "星期",
    "dayweather": "白天天气",
    "nightweather": "夜间天气",
    "daytemp": "白天气温",
    "nighttemp": "夜间气温",
    "daywind": "白天风向",
    "nightwind": "夜间风向",
    "daypower": "白天风力",
    "nightpower": "夜间风力",
}


def _translate_keys_to_zh(data: Any) -> Any:
    """递归将返回结果中的英文 key 翻译为中文。"""
    if isinstance(data, dict):
        return {_KEY_ZH_MAP.get(k, k): _translate_keys_to_zh(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_translate_keys_to_zh(item) for item in data]
    return data


def pretty_print_weather(data: Dict[str, Any]) -> None:
    """
    以更美观的 JSON 格式输出天气结果，并将 key 翻译为中文。
    """
    zh_data = _translate_keys_to_zh(data)
    print(json.dumps(zh_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    city_input = "丽江"  # 也可以传 adcode，例如 "110000"
    try:
        result = get_weather(city_input)
        pretty_print_weather(result)
    except AMapWeatherAPIError as e:
        print(f"调用失败：{e}")
