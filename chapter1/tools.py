import os

import requests
from tavily import TavilyClient


def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息
    """
    url = f"https://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        current_condition = data["current_condition"][0]
        weather_desc = current_condition["weatherDesc"][0]["value"]
        temp_c = current_condition["temp_C"]

        return f"{city} 当前天气: {weather_desc}, 温度: {temp_c}°C"

    except requests.exceptions.RequestException as e:
        return f"查询天气遇到网络问题 - {e}"

    except (KeyError, IndexError) as e:
        return f"解析天气数据失败，可能是城市名称无效 - {e}"


def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气, 使用Tavily Search API搜索并返回优化后的景点推荐。
    """

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Tavily API Key 未设置，请在环境变量中设置 TAVILY_API_KEY"

    # 初始化 Tavily 客户端
    tavily = TavilyClient(api_key=api_key)

    query = f"'{city}' 在 '{weather}' 天气下最值得去的旅游景点推荐及理由"

    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为你找到一下信息： \n" + "\n".join(formatted_results)

    except Exception as e:
        return f"执行Tavily搜索时出现问题 - {e}"
