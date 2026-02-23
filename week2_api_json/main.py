from github_api import fetch_repo, search_repos


def main():
    # 1) 拉取一个repo的信息
    repo_info = fetch_repo("Francis-moon", "ai-lab")
    print("Repo:", repo_info.full_name)
    print("Stars:", repo_info.stars, "Forks:", repo_info.forks, "Open Issues:" ,repo_info.open_issues)
    print("Description:", repo_info.description)
    print("-" * 50)

    # 2) 搜索: 把query换成你感兴趣的关键词,比如"langgraph", "open claw"等
    total, repos = search_repos("langgraph", top_n=3)
    print("Search total:", total)
    for i, repo in enumerate(repos, 1):
        print(f"{i}.{repo.full_name}, Stars: {repo.stars}, Forks: {repo.forks}, Open Issues: {repo.open_issues}")

if __name__ == "__main__":
    main()