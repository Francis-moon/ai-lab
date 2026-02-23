from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()   # 读取.env（如果存在）中的环境变量

DEFAULT_TIMEOUT = 15  # 请求超时时间（秒）


class GitHubAPIError(RuntimeError):
    pass


def _header() -> Dict[str, str]:
    """
    构建GitHub API请求头
    Accept：告诉GitHub你想要 JSON 格式（GitHub官方推荐的媒体类型）
    包含认证（如果提供了GITHUB_TOKEN）。
    """
    h = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        h["Authorization"] = f"bearer {token}"
    return h

def get_json(url: str, *, params: Optional[Dict[str, Any]] = None, retries: int = 3) -> Dict[str, Any]:
    """
    通用GET请求函数,带有重试机制和错误处理。
    - 自动处理非200响应,抛出GitHubAPIError异常。
    - 简单重试（网络抖动/临时失败）
    - 返回dict (JSON)
    """
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=_header(), params=params, timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            else:   # 常见403（限流）、404（资源不存在）、500等错误
                raise GitHubAPIError(f"GitHub API error: GET{url} failed: {response.status_code} {response.text}")
        
        except (requests.RequestException, GitHubAPIError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))  # 递增等待
                continue
            raise GitHubAPIError(f"GitHub API error: GET{url} failed after {retries} attempts: {str(e)}") from e
        
    # 理论上不应该到达这里，因为上面会抛出异常
    raise GitHubAPIError(f"GitHub API error: GET{url} failed after {last_err}")


@dataclass
class RepoInfo:
    """
    把 GitHub 返回的巨大JSON，压缩成关心的5个字段。
    """
    full_name: str
    stars: int
    forks: int
    open_issues: int
    description: Optional[str]

def fetch_repo(owner: str, repo: str) -> RepoInfo:
    """
    获取GitHub仓库的基本信息,忽略其他信息。
    - owner: 仓库所有者用户名
    - repo: 仓库名称
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    data = get_json(url)
    return RepoInfo(
        full_name=data["full_name"],
        stars=int(data["stargazers_count"]),
        forks=int(data["forks_count"]),
        open_issues=int(data["open_issues_count"]),
        description=data.get("description"),
    )


def search_repos(query: str, top_n: int = 5) -> Tuple[int, list[RepoInfo]]:
    """
    搜索GitHub仓库,返回总结果数和前N个仓库信息。
    - query: 搜索关键词
    - top_n: 返回的仓库数量（默认5）
    """
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": top_n}
    data = get_json(url, params=params)
    total_count = int(data["total_count"])
    items = data.get("items", [])
    
    repos: list[RepoInfo] = []
    for item in items:
        repos.append(RepoInfo(
            full_name=item["full_name"],
            stars=int(item["stargazers_count"]),
            forks=int(item["forks_count"]),
            open_issues=int(item["open_issues_count"]),
            description=item.get("description"),
        ))
    return total_count, repos


if __name__ == "__main__":
    # 简单测试
    h = _header()  # 确保环境变量读取正常
    print("Headers:", h)
