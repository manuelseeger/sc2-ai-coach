import requests

PROFILE_BASE = "https://starcraft2.com/en-us/profile/"
API_BASE = "https://starcraft2.blizzard.com/en-us/api/sc2/profile/"


def smurf_detection_summary(toon_handle):
    summary = {}

    handle = toon_handle.replace("-S2-", "/").replace("-", "/")

    profile_url = PROFILE_BASE + handle
    api_url = API_BASE + handle

    with requests.Session() as s:
        r = s.get(api_url)

        profile = r.json()

        summary["career"] = profile["career"]
        summary["snapshot"] = profile["snapshot"]

        return summary


def main():
    summary = smurf_detection_summary("2-S2-1-8019265")
    print(summary)


if __name__ == "__main__":
    main()
